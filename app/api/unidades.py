from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.models import Unidade
from app.api.schemas import UnidadeResposta

router = APIRouter(prefix="/unidades", tags=["Unidades"])


@router.get("/", response_model=list[UnidadeResposta])
def listar_unidades(db: Session = Depends(get_db)):
    consulta = select(Unidade).where(Unidade.status == "ATIVA")
    unidades = db.scalars(consulta).all()

    return unidades