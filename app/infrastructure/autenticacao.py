
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError

from app.infrastructure.config import configuracoes

ALGORITHM = "HS256"

def criar_token_acesso(id_usuario: int) -> str:
    agora = datetime.now(timezone.utc)

    payload = {
        "sub": str(id_usuario),
        "exp": agora + timedelta(
            minutes=configuracoes.access_token_expire_minutes
        ),
    }

    token = jwt.encode(
        payload,
        configuracoes.secret_key,
        algorithm=ALGORITHM,
    )

    return token

def decodificar_token(token: str) -> dict | None:
    try:
        dados = jwt.decode(
            token,
            configuracoes.secret_key,
            algorithms=[ALGORITHM],
        )

        return dados

    except InvalidTokenError:
        return None