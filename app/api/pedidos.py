
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.api.dependencias import obter_usuario_atual
from app.api.schemas import (
    PedidoCriacao,
    PedidoResposta,
    PedidoConsultaResposta,
    PedidoDetalheResposta,
    ItemPedidoResposta,
    PagamentoEntrada,
    CancelamentoPedidoEntrada,
    AtualizacaoStatusPedidoEntrada,
)
from app.infrastructure.models import Usuario, UsuarioUnidade, Pedido, ItemPedido
from app.application.pedido_service import (
    criar_pedido,
    cancelar_pedido,
    marcar_pedido_pronto,
)
from app.application.pagamento_service import processar_pagamento


router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def obter_unidades_atendente(db: Session, usuario: Usuario) -> list[int]:
    if usuario.perfil != "ATENDENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido somente a clientes e atendentes",
        )

    unidades = (
        db.query(UsuarioUnidade.id_unidade)
        .filter(
            UsuarioUnidade.id_usuario == usuario.id_usuario,
            UsuarioUnidade.ativo.is_(True),
        )
        .all()
    )

    ids_unidades = [unidade[0] for unidade in unidades]

    if not ids_unidades:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Atendente não possui vínculo ativo com nenhuma unidade",
        )

    return ids_unidades


@router.post(
    "",
    response_model=PedidoResposta,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_pedido(
    dados: PedidoCriacao,
    chave_idempotencia: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=255,
    ),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
):
    return criar_pedido(
        db=db,
        dados=dados,
        usuario=usuario,
        chave_idempotencia=chave_idempotencia,
    )


@router.get(
    "",
    response_model=list[PedidoConsultaResposta],
)
def listar_pedidos(
    canal_pedido: str | None = Query(default=None, alias="canalPedido"),
    status_pedido: str | None = Query(default=None, alias="status"),
    id_unidade: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
):
    consulta = db.query(Pedido)

    if usuario.perfil == "CLIENTE":
        consulta = consulta.filter(
            Pedido.id_cliente == usuario.id_usuario
        )

    elif usuario.perfil == "ATENDENTE":
        unidades_ids = obter_unidades_atendente(db, usuario)

        consulta = consulta.filter(
            Pedido.id_unidade.in_(unidades_ids)
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem permissão para listar pedidos",
        )

    if canal_pedido is not None:
        consulta = consulta.filter(
            Pedido.canal_pedido == canal_pedido.upper()
        )

    if status_pedido is not None:
        consulta = consulta.filter(
            Pedido.status_pedido == status_pedido.upper()
        )

    if id_unidade is not None:
        consulta = consulta.filter(
            Pedido.id_unidade == id_unidade
        )

    pedidos = (
        consulta
        .order_by(Pedido.data_pedido.desc(), Pedido.id_pedido.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return pedidos


@router.get(
    "/{id_pedido}",
    response_model=PedidoDetalheResposta,
)
def consultar_pedido(
    id_pedido: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
):
    pedido = (
        db.query(Pedido)
        .filter(Pedido.id_pedido == id_pedido)
        .first()
    )

    if pedido is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido não encontrado",
        )

    if usuario.perfil == "CLIENTE":
        if pedido.id_cliente != usuario.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido não encontrado",
            )

    elif usuario.perfil == "ATENDENTE":
        unidades_ids = obter_unidades_atendente(db, usuario)

        if pedido.id_unidade not in unidades_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido não encontrado",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem permissão para consultar pedidos",
        )

    itens = (
        db.query(ItemPedido)
        .filter(ItemPedido.id_pedido == id_pedido)
        .all()
    )

    return PedidoDetalheResposta(
        id_pedido=pedido.id_pedido,
        id_unidade=pedido.id_unidade,
        canal_pedido=pedido.canal_pedido,
        status_pedido=pedido.status_pedido,
        valor_total=pedido.valor_total,
        data_pedido=pedido.data_pedido,
        data_limite_pagamento=pedido.data_limite_pagamento,
        itens=[
            ItemPedidoResposta(
                id_produto_unidade=item.id_produto_unidade,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
                subtotal=item.subtotal,
            )
            for item in itens
        ],
    )


@router.post(
    "/{id_pedido}/pagamento",
    status_code=status.HTTP_200_OK,
)
def realizar_pagamento(
    id_pedido: int,
    dados: PagamentoEntrada,
    chave_idempotencia: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=255,
    ),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
):
    return processar_pagamento(
        db=db,
        id_pedido=id_pedido,
        dados=dados,
        usuario=usuario,
        chave_idempotencia=chave_idempotencia,
    )


@router.post("/{id_pedido}/cancelar")
def cancelar_pedido_endpoint(
    id_pedido: int,
    dados: CancelamentoPedidoEntrada,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
):
    return cancelar_pedido(
        db=db,
        id_pedido=id_pedido,
        motivo=dados.motivo,
        usuario=usuario,
    )


@router.patch("/{id_pedido}/status")
def marcar_pedido_pronto_endpoint(
    id_pedido: int,
    dados: AtualizacaoStatusPedidoEntrada,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
):
    return marcar_pedido_pronto(
        db=db,
        id_pedido=id_pedido,
        observacao=dados.observacao,
        usuario=usuario,
    )
