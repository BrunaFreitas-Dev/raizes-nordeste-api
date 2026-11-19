from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.models import Estoque
from app.api.schemas import EntradaEstoque
from app.api.dependencias import exigir_perfil

router = APIRouter(prefix="/estoque", tags=["Estoque"])


@router.post(
    "/{id_produto_unidade}/entrada",
    status_code=status.HTTP_200_OK,
)
def registrar_entrada_estoque(
    id_produto_unidade: int,
    dados: EntradaEstoque,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_perfil("GERENTE", "ADMINISTRADOR")),
):
    estoque = (
        db.query(Estoque)
        .filter(
            Estoque.id_produto_unidade == id_produto_unidade
        )
        .with_for_update()
        .first()
    )

    if estoque is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estoque não encontrado",
        )

    estoque.quantidade_total += dados.quantidade

    try:
        db.commit()
        db.refresh(estoque)
    except Exception:
        db.rollback()
        raise

    return {
        "mensagem": "Entrada de estoque registrada com sucesso",
        "id_estoque": estoque.id_estoque,
        "quantidade_total": estoque.quantidade_total,
        "quantidade_reservada": estoque.quantidade_reservada,
    }