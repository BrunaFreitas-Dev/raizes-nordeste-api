from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    String,
    CheckConstraint,
    Text,
    ForeignKey,
    Numeric,
    Boolean,
    UniqueConstraint,
    Integer,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class Unidade(Base):
    __tablename__ = "unidade"

    id_unidade: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    endereco: Mapped[str] = mapped_column(String(200), nullable=False)
    cidade: Mapped[str] = mapped_column(String(100), nullable=False )
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    telefone: Mapped[str] = mapped_column(String(20), nullable=False)
    regiao: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)


    __table_args__ = (
        CheckConstraint(
            "regiao IN ('NORTE', 'NORDESTE', 'CENTRO_OESTE', 'SUDESTE', 'SUL')",
            name="ck_unidade_regiao"
        ),
        CheckConstraint(
            "status IN ('ATIVA', 'INATIVA')",
            name="ck_unidade_status"
        ),
    )


class Produto(Base):
    __tablename__ = "produto"

    id_produto: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('ATIVO', 'INATIVO')",
            name="ck_produto_status"
        ),
    )


class ProdutoUnidade(Base):
    __tablename__ = "produto_unidade"

    id_produto_unidade: Mapped[int] = mapped_column(primary_key=True)

    id_unidade: Mapped[int] = mapped_column(
        ForeignKey("unidade.id_unidade"), 
        nullable=False
    )

    id_produto: Mapped[int] = mapped_column(
        ForeignKey("produto.id_produto"),
        nullable=False
    )

    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    disponivel: Mapped[bool] = mapped_column(Boolean, nullable=False)


    __table_args__ = (
        UniqueConstraint(
            "id_unidade",
            "id_produto",
            name="uq_produto_unidade"
        ),
        CheckConstraint(
            "preco > 0",
            name="ck_produto_unidade_preco"
        ),
    )


class Estoque(Base):
    __tablename__ = "estoque"

    id_estoque: Mapped[int] = mapped_column(primary_key=True)

    id_produto_unidade: Mapped[int] = mapped_column(
        ForeignKey("produto_unidade.id_produto_unidade"),
        unique=True,
        nullable=False
    )

    quantidade_reservada: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
    )

    quantidade_total: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "quantidade_total >= 0",
            name="ck_estoque_total"
        ),
        CheckConstraint(
            "quantidade_reservada >= 0",
            name="ck_estoque_reservada"     
        ),
        CheckConstraint(
            "quantidade_reservada <= quantidade_total",
            name="ck_estoque_reserva_limite"
        ),
    )


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(primary_key=True)

    nome: Mapped[str] = mapped_column(
        String(100), 
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False
    )

    senha_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    perfil: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )

    data_cadastro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )    

    __table_args__ = (
        CheckConstraint(
            "perfil IN ('CLIENTE', 'ATENDENTE', 'GERENTE', 'ADMINISTRADOR')",
            name="ck_usuario_perfil"
        ),
    )


class UsuarioUnidade(Base):
    __tablename__ = "usuario_unidade"

    id_usuario_unidade: Mapped[int] = mapped_column(
        primary_key=True
    )

    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id_usuario"),
        nullable=False    
    )

    id_unidade: Mapped[int] = mapped_column(
        ForeignKey("unidade.id_unidade"),
        nullable=False
    )

    data_vinculo: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )        

    __table_args__ = (
        UniqueConstraint(
            "id_usuario",
            "id_unidade",
            name="uq_usuario_unidade"
        ),
    )





