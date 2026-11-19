from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import HTTPException, status
from app.infrastructure.models import Produto, ProdutoUnidade
from app.api.schemas import ItemCardapioResposta

from app.infrastructure.database import get_db
from app.infrastructure.models import Unidade
from app.api.schemas import UnidadeResposta

router = APIRouter(prefix="/unidades", tags=["Unidades"])


@router.get("/", response_model=list[UnidadeResposta])
def listar_unidades(db: Session = Depends(get_db)):
    consulta = select(Unidade).where(Unidade.status == "ATIVA")
    unidades = db.scalars(consulta).all()

    return unidades

@router.get(
    "/{id_unidade}/cardapio",
    response_model=list[ItemCardapioResposta],
)
def consultar_cardapio(
    id_unidade: int,
    db: Session = Depends(get_db),
):
    unidade = db.get(Unidade, id_unidade)

    if unidade is None or unidade.status != "ATIVA":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unidade não encontrada ou inativa",
        )

    consulta = (
        select(
            Produto.id_produto,
            Produto.nome,
            Produto.descricao,
            Produto.categoria,
            ProdutoUnidade.preco,
            ProdutoUnidade.disponivel,
        )
        .join(
            ProdutoUnidade,
            ProdutoUnidade.id_produto == Produto.id_produto,
        )
        .where(
            ProdutoUnidade.id_unidade == id_unidade,
            Produto.status == "ATIVO",
        )
    )

    resultados = db.execute(consulta).mappings().all()

    return [dict(item) for item in resultados]