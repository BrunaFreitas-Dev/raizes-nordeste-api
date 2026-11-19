
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CadastroUsuario(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)

    model_config = ConfigDict(extra="forbid")


class UsuarioResposta(BaseModel):
    id_usuario: int
    nome: str
    email: EmailStr
    perfil: str
    ativo: bool
    data_cadastro: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResposta(BaseModel):
    access_token: str
    token_type: str
