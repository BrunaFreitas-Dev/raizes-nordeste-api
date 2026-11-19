
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import Usuario
from app.infrastructure.seguranca import verificar_senha
from app.infrastructure.autenticacao import criar_token_acesso


def autenticar_usuario(db: Session, email: str, senha: str) -> dict:
    usuario = db.scalar(
        select(Usuario).where(Usuario.email == email)
    )

    # A mesma mensagem evita revelar se o e-mail existe
    if (
        usuario is None
        or not usuario.ativo
        or not verificar_senha(senha, usuario.senha_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenciais inválidas",
        )

    token = criar_token_acesso(usuario.id_usuario)

    return {
        "access_token": token,
        "token_type": "bearer",
    }
