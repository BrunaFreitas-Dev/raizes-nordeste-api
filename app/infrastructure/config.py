from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int
    modo_pagamento: str

    model_config = SettingsConfigDict(env_file=".env")


configuracoes = Configuracoes()       