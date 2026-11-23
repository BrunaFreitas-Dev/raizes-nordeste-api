
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import secrets
import bcrypt

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.schemas import PedidoCriacao
from app.domain.enums import StatusPedido
from app.infrastructure.models import (
    Unidade,
    Produto,
    ProdutoUnidade,
    Estoque,
    Pedido,
    ItemPedido,
    MovimentacaoEstoque,
    HistoricoStatusPedido,
    Auditoria,
    Usuario,
    UsuarioUnidade,
)


def criar_pedido(
    db: Session,
    dados: PedidoCriacao,
    usuario: Usuario,
    chave_idempotencia: str,
) -> dict:
    pedido_existente = db.scalar(
        select(Pedido).where(
            Pedido.chave_idempotencia_criacao == chave_idempotencia
        )
    )

    if pedido_existente:
        raise HTTPException(
            status_code=409,
            detail="Chave de idempotência já utilizada",
        )

    canal = dados.canal_pedido.value

    if usuario.perfil == "CLIENTE":
        permitido = canal in ("APP", "WEB")
    elif usuario.perfil == "ATENDENTE":
        if usuario.usuario_tecnico:
            permitido = canal in ("TOTEM", "PICKUP")
        else:
            permitido = canal == "BALCAO"
    else:
        permitido = False

    if not permitido:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seu perfil não tem permissão para criar pedidos neste canal",
        )

    unidade = db.get(Unidade, dados.id_unidade)

    if unidade is None or unidade.status != "ATIVA":
        raise HTTPException(
            status_code=404,
            detail="Unidade não encontrada ou inativa",
        )

    if usuario.perfil == "ATENDENTE":
        vinculo = db.scalar(
            select(UsuarioUnidade).where(
                UsuarioUnidade.id_usuario == usuario.id_usuario,
                UsuarioUnidade.id_unidade == dados.id_unidade,
                UsuarioUnidade.ativo.is_(True),
            )
        )

        if vinculo is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não está vinculado a esta unidade",
            )

    quantidades = {}

    for item in dados.itens:
        id_produto_unidade = item.id_produto_unidade
        quantidades[id_produto_unidade] = (
            quantidades.get(id_produto_unidade, 0) + item.quantidade
        )

    itens_calculados = []
    valor_total = Decimal("0.00")

    for id_produto_unidade, quantidade in quantidades.items():
        resultado = db.execute(
            select(ProdutoUnidade, Produto, Estoque)
            .join(
                Produto,
                Produto.id_produto == ProdutoUnidade.id_produto,
            )
            .join(
                Estoque,
                Estoque.id_produto_unidade
                == ProdutoUnidade.id_produto_unidade,
            )
            .where(
                ProdutoUnidade.id_produto_unidade
                == id_produto_unidade,
                ProdutoUnidade.id_unidade == dados.id_unidade,
            )
        ).first()

        if resultado is None:
            raise HTTPException(
                status_code=404,
                detail=f"Produto {id_produto_unidade} não encontrado nesta unidade",
            )

        produto_unidade, produto, estoque = resultado

        if produto.status != "ATIVO" or not produto_unidade.disponivel:
            raise HTTPException(
                status_code=409,
                detail=f"Produto {produto.nome} indisponível",
            )

        disponivel = (
            estoque.quantidade_total - estoque.quantidade_reservada
        )

        if disponivel < quantidade:
            raise HTTPException(
                status_code=409,
                detail=f"Estoque insuficiente para {produto.nome}",
            )

        preco = produto_unidade.preco
        subtotal = preco * quantidade
        valor_total += subtotal

        itens_calculados.append({
            "id_produto_unidade": id_produto_unidade,
            "quantidade": quantidade,
            "preco_unitario": preco,
            "subtotal": subtotal,
            "id_estoque": estoque.id_estoque,
        })

    codigo_acompanhamento = secrets.token_urlsafe(12)

    codigo_hash = bcrypt.hashpw(
        codigo_acompanhamento.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    agora = datetime.now(timezone.utc)

    id_cliente = (
        usuario.id_usuario
        if usuario.perfil == "CLIENTE"
        else None
    )

    id_registrado_por = (
        usuario.id_usuario
        if usuario.perfil != "CLIENTE"
        else None
    )

    origem_ator = (
        "USUARIO_TECNICO"
        if usuario.perfil == "ATENDENTE" and usuario.usuario_tecnico
        else usuario.perfil
    )

    try:
        pedido = Pedido(
            id_cliente=id_cliente,
            id_registrado_por=id_registrado_por,
            id_unidade=dados.id_unidade,
            id_credencial=None,
            canal_pedido=dados.canal_pedido.value,
            status_pedido=StatusPedido.AGUARDANDO_PAGAMENTO.value,
            valor_total=valor_total,
            data_pedido=agora,
            data_limite_pagamento=agora + timedelta(minutes=30),
            motivo_cancelamento=None,
            codigo_acompanhamento_hash=codigo_hash,
            chave_idempotencia_criacao=chave_idempotencia,
        )

        db.add(pedido)
        db.flush()

        for item in itens_calculados:
            resultado_reserva = db.execute(
                update(Estoque)
                .where(
                    Estoque.id_estoque == item["id_estoque"],
                    (
                        Estoque.quantidade_total
                        - Estoque.quantidade_reservada
                    ) >= item["quantidade"],
                )
                .values(
                    quantidade_reservada=(
                        Estoque.quantidade_reservada
                        + item["quantidade"]
                    )
                )
            )

            if resultado_reserva.rowcount != 1:
                raise HTTPException(
                    status_code=409,
                    detail="Estoque insuficiente para concluir o pedido",
                )

            db.add(
                ItemPedido(
                    id_pedido=pedido.id_pedido,
                    id_produto_unidade=item["id_produto_unidade"],
                    quantidade=item["quantidade"],
                    preco_unitario=item["preco_unitario"],
                    subtotal=item["subtotal"],
                )
            )

            db.add(
                MovimentacaoEstoque(
                    id_estoque=item["id_estoque"],
                    id_usuario=usuario.id_usuario,
                    id_pedido=pedido.id_pedido,
                    tipo_movimentacao="RESERVA",
                    quantidade=item["quantidade"],
                    observacao="Reserva de estoque para pedido",
                )
            )

        db.add(
            HistoricoStatusPedido(
                id_pedido=pedido.id_pedido,
                id_usuario=usuario.id_usuario,
                id_credencial=None,
                origem_ator=origem_ator,
                status_anterior=None,
                status_novo=StatusPedido.AGUARDANDO_PAGAMENTO.value,
                observacao="Pedido criado",
            )
        )

        db.add(
            Auditoria(
                id_usuario=usuario.id_usuario,
                id_pedido=pedido.id_pedido,
                id_credencial=None,
                origem_ator=origem_ator,
                acao="CRIACAO_PEDIDO",
                descricao="Pedido criado e estoque reservado",
                dados_anteriores=None,
                dados_posteriores=json.dumps({
                    "status_pedido": StatusPedido.AGUARDANDO_PAGAMENTO.value,
                    "valor_total": str(valor_total),
                    "canal_pedido": dados.canal_pedido.value,
                }),
            )
        )

        db.commit()
        db.refresh(pedido)

        return {
            "id_pedido": pedido.id_pedido,
            "id_unidade": pedido.id_unidade,
            "canal_pedido": pedido.canal_pedido,
            "status_pedido": pedido.status_pedido,
            "valor_total": pedido.valor_total,
            "data_pedido": pedido.data_pedido,
            "data_limite_pagamento": pedido.data_limite_pagamento,
            "codigo_acompanhamento": codigo_acompanhamento,
        }

    except Exception:
        db.rollback()
        raise


def cancelar_pedido(
    db: Session,
    id_pedido: int,
    motivo: str,
    usuario: Usuario,
) -> dict:
    pedido = db.get(Pedido, id_pedido)

    if pedido is None:
        raise HTTPException(
            status_code=404,
            detail="Pedido não encontrado",
        )

    if usuario.perfil == "CLIENTE":
        if pedido.id_cliente != usuario.id_usuario:
            raise HTTPException(
                status_code=403,
                detail="Você não pode cancelar este pedido",
            )
    elif usuario.perfil == "ATENDENTE":
        vinculo = db.scalar(
            select(UsuarioUnidade).where(
                UsuarioUnidade.id_usuario == usuario.id_usuario,
                UsuarioUnidade.id_unidade == pedido.id_unidade,
                UsuarioUnidade.ativo.is_(True),
            )
        )

        if vinculo is None:
            raise HTTPException(
                status_code=403,
                detail="Você não está vinculado a esta unidade",
            )
    else:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para cancelar pedidos",
        )

    if pedido.status_pedido not in (
        StatusPedido.AGUARDANDO_PAGAMENTO.value,
        StatusPedido.FALHA_PAGAMENTO.value,
    ):
        raise HTTPException(
            status_code=409,
            detail="Este pedido não pode ser cancelado neste status",
        )

    status_anterior = pedido.status_pedido

    itens = db.execute(
        select(ItemPedido, Estoque)
        .join(
            Estoque,
            Estoque.id_produto_unidade
            == ItemPedido.id_produto_unidade,
        )
        .where(ItemPedido.id_pedido == id_pedido)
    ).all()

    origem_ator = (
        "USUARIO_TECNICO"
        if usuario.perfil == "ATENDENTE" and usuario.usuario_tecnico
        else usuario.perfil
    )

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
                        Estoque.quantidade_reservada
                        - item.quantidade
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
                    observacao="Liberação de reserva por cancelamento manual",
                )
            )

        pedido.status_pedido = StatusPedido.CANCELADO.value
        pedido.motivo_cancelamento = motivo

        db.add(
            HistoricoStatusPedido(
                id_pedido=pedido.id_pedido,
                id_usuario=usuario.id_usuario,
                id_credencial=None,
                origem_ator=origem_ator,
                status_anterior=status_anterior,
                status_novo=StatusPedido.CANCELADO.value,
                observacao=f"Pedido cancelado manualmente: {motivo}",
            )
        )

        db.add(
            Auditoria(
                id_usuario=usuario.id_usuario,
                id_pedido=pedido.id_pedido,
                id_credencial=None,
                origem_ator=origem_ator,
                acao="CANCELAMENTO_MANUAL",
                descricao="Pedido cancelado manualmente e estoque liberado",
                dados_anteriores=json.dumps({
                    "status_pedido": status_anterior,
                }),
                dados_posteriores=json.dumps({
                    "status_pedido": StatusPedido.CANCELADO.value,
                    "motivo_cancelamento": motivo,
                }),
            )
        )

        db.commit()
        db.refresh(pedido)

        return {
            "id_pedido": pedido.id_pedido,
            "status_pedido": pedido.status_pedido,
            "motivo_cancelamento": pedido.motivo_cancelamento,
            "mensagem": "Pedido cancelado e estoque liberado com sucesso",
        }

    except Exception:
        db.rollback()
        raise


def marcar_pedido_pronto(
    db: Session,
    id_pedido: int,
    observacao: str | None,
    usuario: Usuario,
) -> dict:
    pedido = db.get(Pedido, id_pedido)

    if pedido is None:
        raise HTTPException(
            status_code=404,
            detail="Pedido não encontrado",
        )

    if usuario.perfil != "ATENDENTE":
        raise HTTPException(
            status_code=403,
            detail="Somente atendentes podem atualizar este status",
        )

    vinculo = db.scalar(
        select(UsuarioUnidade).where(
            UsuarioUnidade.id_usuario == usuario.id_usuario,
            UsuarioUnidade.id_unidade == pedido.id_unidade,
            UsuarioUnidade.ativo.is_(True),
        )
    )

    if vinculo is None:
        raise HTTPException(
            status_code=403,
            detail="Você não está vinculado a esta unidade",
        )

    if pedido.status_pedido != StatusPedido.PAGO.value:
        raise HTTPException(
            status_code=409,
            detail="Somente pedidos pagos podem ficar prontos para retirada",
        )

    status_anterior = pedido.status_pedido
    novo_status = StatusPedido.PRONTO_PARA_RETIRADA.value

    origem_ator = (
        "USUARIO_TECNICO"
        if usuario.usuario_tecnico
        else usuario.perfil
    )

    try:
        pedido.status_pedido = novo_status

        db.add(
            HistoricoStatusPedido(
                id_pedido=pedido.id_pedido,
                id_usuario=usuario.id_usuario,
                id_credencial=None,
                origem_ator=origem_ator,
                status_anterior=status_anterior,
                status_novo=novo_status,
                observacao=(
                    observacao
                    or "Pedido marcado como pronto para retirada"
                ),
            )
        )

        db.add(
            Auditoria(
                id_usuario=usuario.id_usuario,
                id_pedido=pedido.id_pedido,
                id_credencial=None,
                origem_ator=origem_ator,
                acao="ATUALIZACAO_STATUS_PEDIDO",
                descricao="Pedido marcado como pronto para retirada",
                dados_anteriores=json.dumps({
                    "status_pedido": status_anterior,
                }),
                dados_posteriores=json.dumps({
                    "status_pedido": novo_status,
                    "observacao": observacao,
                }),
            )
        )

        db.commit()
        db.refresh(pedido)

        return {
            "id_pedido": pedido.id_pedido,
            "status_pedido": pedido.status_pedido,
            "mensagem": "Pedido marcado como pronto para retirada",
        }

    except Exception:
        db.rollback()
        raise
