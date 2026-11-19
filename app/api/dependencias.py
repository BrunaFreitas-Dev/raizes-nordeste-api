
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.models import Usuario
from app.infrastructure.autenticacao import decodificar_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def obter_usuario_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:

    dados_token = decodificar_token(token)

    if dados_token is None or "sub" not in dados_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        id_usuario = int(dados_token["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = db.scalar(
        select(Usuario).where(Usuario.id_usuario == id_usuario)
    )

    if usuario is None or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


def exigir_perfil(*perfis_permitidos: str):

    def verificar_perfil(
        usuario: Usuario = Depends(obter_usuario_atual),
    ) -> Usuario:

        if usuario.perfil not in perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este recurso",
            )

        return usuario

    return verificar_perfil
