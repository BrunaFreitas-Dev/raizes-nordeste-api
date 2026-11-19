
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.models import Usuario
from app.infrastructure.seguranca import gerar_hash_senha
from app.api.schemas import CadastroUsuario, UsuarioResposta

from fastapi.security import OAuth2PasswordRequestForm

from app.api.schemas import TokenResposta
from app.application.auth_service import autenticar_usuario

from app.api.dependencias import obter_usuario_atual


router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/cadastro",
    response_model=UsuarioResposta,
    status_code=status.HTTP_201_CREATED,
)
def cadastrar_usuario(
    dados: CadastroUsuario,
    db: Session = Depends(get_db),
):
    usuario_existente = db.scalar(
        select(Usuario).where(Usuario.email == dados.email)
    )

    if usuario_existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado",
        )

    novo_usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.senha),
        perfil="CLIENTE",
        ativo=True,
    )

    try:
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado",
        )

    return novo_usuario


@router.post("/login", response_model=TokenResposta)
def login(
    formulario: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return autenticar_usuario(
        db,
        formulario.username,
        formulario.password,
    )


@router.get("/me", response_model=UsuarioResposta)
def obter_me(
    usuario: Usuario = Depends(obter_usuario_atual),
):
    return usuario