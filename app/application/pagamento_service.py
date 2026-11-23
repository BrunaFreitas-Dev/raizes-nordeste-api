
from datetime import datetime, timezone
import json
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.schemas import PagamentoEntrada
from app.domain.enums import StatusPedido
from app.infrastructure.config import configuracoes
from app.infrastructure.models import (
    Pedido,
    TentativaPagamento,
    ItemPedido,
    Estoque,
    MovimentacaoEstoque,
    HistoricoStatusPedido,
    Auditoria,
    Usuario,
)


def _normalizar_data(data):
    """Garante que a data tenha fuso horário UTC."""
    if data.tzinfo is None:
        return data.replace(tzinfo=timezone.utc)
    return data


def _cancelar_pedido_expirado(
    db: Session,
    pedido: Pedido,
    usuario: Usuario,
    origem_ator: str,
):
    """Cancela o pedido expirado e libera o estoque reservado."""

    status_anterior = pedido.status_pedido

    itens = db.execute(
        select(ItemPedido, Estoque)
        .join(
            Estoque,
            Estoque.id_produto_unidade == ItemPedido.id_produto_unidade,
        )
        .where(ItemPedido.id_pedido == pedido.id_pedido)
    ).all()

    try:
        for item, estoque in itens:
            resultado = db.execute(
                update(Estoque)
                .where(
                    Estoque.id_estoque == estoque.id_estoque,
                    Estoque.quantidade_reservada >= item.quantidade,
                )
                .values(
                    quantidade_reservada=(
                        Estoque.quantidade_reservada - item.quantidade
                    )
                )
            )

            if resultado.rowcount != 1:
                raise HTTPException(
                    status_code=409,
                    detail="Não foi possível liberar a reserva de estoque",
                )

            db.add(
                MovimentacaoEstoque(
                    id_estoque=estoque.id_estoque,
                    id_usuario=usuario.id_usuario,
                    id_pedido=pedido.id_pedido,
                    tipo_movimentacao="LIBERACAO",
                    quantidade=item.quantidade,
                    observacao="Liberação de reserva por expiração do pagamento",
                )
            )

        pedido.status_pedido = StatusPedido.CANCELADO.value
        pedido.motivo_cancelamento = "PRAZO_PAGAMENTO_EXPIRADO"

        db.add(
            HistoricoStatusPedido(
                id_pedido=pedido.id_pedido,
                id_usuario=usuario.id_usuario,
                id_credencial=None,
                origem_ator=origem_ator,
                status_anterior=status_anterior,
                status_novo=StatusPedido.CANCELADO.value,
                observacao="Pedido cancelado por expiração do prazo de pagamento",
            )
        )

        db.add(
            Auditoria(
                id_usuario=usuario.id_usuario,
                id_pedido=pedido.id_pedido,
                id_credencial=None,
                origem_ator=origem_ator,
                acao="CANCELAMENTO_POR_EXPIRACAO",
                descricao="Pedido cancelado e estoque reservado liberado",
                dados_anteriores=json.dumps({
                    "status_pedido": status_anterior,
                }),
                dados_posteriores=json.dumps({
                    "status_pedido": StatusPedido.CANCELADO.value,
                    "motivo_cancelamento": "PRAZO_PAGAMENTO_EXPIRADO",
                }),
            )
        )

        db.commit()

    except Exception:
        db.rollback()
        raise


def processar_pagamento(
    db: Session,
    id_pedido: int,
    dados: PagamentoEntrada,
    usuario: Usuario,
    chave_idempotencia: str,
) -> dict:

    if configuracoes.modo_pagamento.upper() != "MOCK":
        raise HTTPException(
            status_code=501,
            detail="Este serviço está configurado apenas para pagamento MOCK",
        )

    pedido = db.get(Pedido, id_pedido)

    if pedido is None:
        raise HTTPException(
            status_code=404,
            detail="Pedido não encontrado",
        )

    if (
        pedido.id_cliente != usuario.id_usuario
        and pedido.id_registrado_por != usuario.id_usuario
    ):
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para pagar este pedido",
        )

    tentativa_existente = db.scalar(
        select(TentativaPagamento).where(
            TentativaPagamento.chave_idempotencia == chave_idempotencia
        )
    )

    if tentativa_existente:
        if tentativa_existente.id_pedido != id_pedido:
            raise HTTPException(
                status_code=409,
                detail="Chave de idempotência já utilizada em outro pedido",
            )

        return {
            "id_tentativa": tentativa_existente.id_tentativa,
            "id_pedido": id_pedido,
            "status_pagamento": (
                "RECUSADO"
                if tentativa_existente.mensagem_recusa
                else "APROVADO"
            ),
            "status_pedido": pedido.status_pedido,
            "mensagem": "Tentativa já processada anteriormente",
        }

    if pedido.status_pedido not in (
        StatusPedido.AGUARDANDO_PAGAMENTO.value,
        StatusPedido.FALHA_PAGAMENTO.value,
    ):
        raise HTTPException(
            status_code=409,
            detail="Este pedido não aceita novas tentativas de pagamento",
        )

    origem_ator = (
        "USUARIO_TECNICO"
        if usuario.perfil == "ATENDENTE" and usuario.usuario_tecnico
        else usuario.perfil
    )

    agora = datetime.now(timezone.utc)
    limite = _normalizar_data(pedido.data_limite_pagamento)

    if agora > limite:
        _cancelar_pedido_expirado(
            db=db,
            pedido=pedido,
            usuario=usuario,
            origem_ator=origem_ator,
        )

        raise HTTPException(
            status_code=409,
            detail="Prazo de pagamento expirado. Pedido cancelado.",
        )

    itens = db.execute(
        select(ItemPedido, Estoque)
        .join(
            Estoque,
            Estoque.id_produto_unidade == ItemPedido.id_produto_unidade,
        )
        .where(ItemPedido.id_pedido == id_pedido)
    ).all()

    for item, estoque in itens:
        if estoque.quantidade_reservada < item.quantidade:
            raise HTTPException(
                status_code=409,
                detail="A reserva de estoque não está mais disponível",
            )

    status_anterior = pedido.status_pedido
    resultado_mock = dados.resultado_simulado.value

    if resultado_mock == "APROVADO":
        novo_status = StatusPedido.PAGO.value
        mensagem_recusa = None
    else:
        novo_status = StatusPedido.FALHA_PAGAMENTO.value
        mensagem_recusa = "Pagamento recusado no ambiente MOCK"

    identificador_transacao = (
        "MOCK-" + secrets.token_hex(8).upper()
    )

    payload_envio = {
        "id_pedido": id_pedido,
        "valor": str(pedido.valor_total),
        "forma_pagamento": dados.forma_pagamento,
        "resultado_simulado": resultado_mock,
    }

    payload_resposta = {
        "identificador_transacao": identificador_transacao,
        "resultado": resultado_mock,
        "status_pedido": novo_status,
    }

    try:
        tentativa = TentativaPagamento(
            id_pedido=id_pedido,
            chave_idempotencia=chave_idempotencia,
            forma_pagamento=dados.forma_pagamento,
            payload_envio=json.dumps(payload_envio),
            identificador_transacao_externa=identificador_transacao,
            payload_resposta=json.dumps(payload_resposta),
            mensagem_recusa=mensagem_recusa,
            status_estorno=None,
        )

        db.add(tentativa)

        pedido.status_pedido = novo_status

        db.add(
            HistoricoStatusPedido(
                id_pedido=id_pedido,
                id_usuario=usuario.id_usuario,
                id_credencial=None,
                origem_ator=origem_ator,
                status_anterior=status_anterior,
                status_novo=novo_status,
                observacao=(
                    "Pagamento aprovado no ambiente MOCK"
                    if resultado_mock == "APROVADO"
                    else "Pagamento recusado no ambiente MOCK"
                ),
            )
        )

        db.add(
            Auditoria(
                id_usuario=usuario.id_usuario,
                id_pedido=id_pedido,
                id_credencial=None,
                origem_ator=origem_ator,
                acao="PROCESSAMENTO_PAGAMENTO",
                descricao=(
                    "Pagamento aprovado no ambiente MOCK"
                    if resultado_mock == "APROVADO"
                    else "Pagamento recusado no ambiente MOCK"
                ),
                dados_anteriores=json.dumps({
                    "status_pedido": status_anterior,
                }),
                dados_posteriores=json.dumps({
                    "status_pedido": novo_status,
                    "resultado_pagamento": resultado_mock,
                    "forma_pagamento": dados.forma_pagamento,
                }),
            )
        )

        db.commit()
        db.refresh(tentativa)

        return {
            "id_tentativa": tentativa.id_tentativa,
            "id_pedido": id_pedido,
            "status_pagamento": resultado_mock,
            "status_pedido": pedido.status_pedido,
            "identificador_transacao": identificador_transacao,
            "mensagem": (
                "Pagamento aprovado com sucesso"
                if resultado_mock == "APROVADO"
                else "Pagamento recusado"
            ),
        }

    except Exception:
        db.rollback()
        raise
