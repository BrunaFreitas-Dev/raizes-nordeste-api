from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.infrastructure.config import configuracoes


# Conexão com o banco de dados
engine = create_engine(
    configuracoes.database_url, 
    connect_args={"check_same_thread": False}
)


# Ativação das chaves estrangeiras no SQLite
@event.listens_for(engine, "connect")
def ativar_chaves_estrangeiras(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()



# Criação das sessões
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


# Base dos modelos
class Base(DeclarativeBase):
    pass



# Dependência para utilizar o banco nas rotas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

        
