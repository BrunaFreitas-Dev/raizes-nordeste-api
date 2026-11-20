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

    usuario_tecnico: Mapped[bool] = mapped_column(
    Boolean,
    default=False,
    nullable=False
    )

    usuario_tecnico: Mapped[bool] = mapped_column(
    Boolean,
    default=False,
    server_default="0",
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


class MovimentacaoEstoque(Base):
    __tablename__ = "movimentacao_estoque"

    id_movimentacao: Mapped[int] = mapped_column(primary_key=True)

    id_estoque: Mapped[int] = mapped_column(
        ForeignKey("estoque.id_estoque"),
        nullable=False
    )

    id_usuario: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id_usuario"),
        nullable=True
    )

    id_pedido: Mapped[int | None] = mapped_column(
        ForeignKey("pedido.id_pedido"),
        nullable=True
    )

    tipo_movimentacao: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    quantidade: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    data_movimentacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    observacao: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )



class CredencialDispositivo(Base):
    __tablename__ = "credencial_dispositivo"

    id_credencial: Mapped[int] = mapped_column(primary_key=True)

    id_unidade: Mapped[int] = mapped_column(
        ForeignKey("unidade.id_unidade"),
        nullable=False
    )

    nome_dispositivo: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    canal: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    chave_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )

    data_criacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "canal IN ('TOTEM', 'PICKUP')",
            name="ck_credencial_canal"
        ),
    )


class Pedido(Base):
    __tablename__ = "pedido"

    id_pedido: Mapped[int] = mapped_column(primary_key=True)

    id_cliente: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id_usuario"),
        nullable=True
    )

    id_registrado_por: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id_usuario"),
        nullable=True
    )

    id_unidade: Mapped[int] = mapped_column(
        ForeignKey("unidade.id_unidade"),
        nullable=False
    )

    id_credencial: Mapped[int | None] = mapped_column(
        ForeignKey("credencial_dispositivo.id_credencial"),
        nullable=True
    )

    canal_pedido: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    status_pedido: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    data_pedido: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    data_limite_pagamento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    motivo_cancelamento: Mapped[str | None] = mapped_column(
    String(100),
    nullable=True
    )

    codigo_acompanhamento_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    chave_idempotencia_criacao: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )


class ItemPedido(Base):
    __tablename__ = "item_pedido"

    id_item: Mapped[int] = mapped_column(primary_key=True)

    id_pedido: Mapped[int] = mapped_column(
        ForeignKey("pedido.id_pedido"),
        nullable=False
    )

    id_produto_unidade: Mapped[int] = mapped_column(
        ForeignKey("produto_unidade.id_produto_unidade"),
        nullable=False
    )

    quantidade: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    preco_unitario: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )


class TentativaPagamento(Base):
    __tablename__ = "tentativa_pagamento"

    id_tentativa: Mapped[int] = mapped_column(primary_key=True)

    id_pedido: Mapped[int] = mapped_column(
        ForeignKey("pedido.id_pedido"),
        nullable=False
    )

    chave_idempotencia: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    forma_pagamento: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    payload_envio: Mapped[str] = mapped_column(
    Text,
    nullable=False
    )
    
    identificador_transacao_externa: Mapped[str | None] = mapped_column(
    String(100),
    nullable=True
    )

    payload_resposta: Mapped[str | None] = mapped_column(
    Text,
    nullable=True
    )

    mensagem_recusa: Mapped[str | None] = mapped_column(
    Text,
    nullable=True
    )

    status_estorno: Mapped[str | None] = mapped_column(
    String(30),
    nullable=True
    )

    data_tentativa: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class HistoricoStatusPedido(Base):
    __tablename__ = "historico_status_pedido"

    id_historico: Mapped[int] = mapped_column(primary_key=True)

    id_pedido: Mapped[int] = mapped_column(
        ForeignKey("pedido.id_pedido"),
        nullable=False
    )

    id_usuario: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id_usuario"),
        nullable=True
    )

    id_credencial: Mapped[int | None] = mapped_column(
        ForeignKey("credencial_dispositivo.id_credencial"),
        nullable=True
    )

    origem_ator: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    status_anterior: Mapped[str | None] = mapped_column(
    String(30),
    nullable=True
    )

    status_novo: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    data_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    observacao: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )


class Auditoria(Base):
    __tablename__ = "auditoria"

    id_auditoria: Mapped[int] = mapped_column(primary_key=True)

    id_usuario: Mapped[int | None] = mapped_column(
        ForeignKey("usuario.id_usuario"),
        nullable=True
    )

    id_pedido: Mapped[int | None] = mapped_column(
        ForeignKey("pedido.id_pedido"),
        nullable=True
    )

    id_credencial: Mapped[int | None] = mapped_column(
        ForeignKey("credencial_dispositivo.id_credencial"),
        nullable=True
    )

    origem_ator: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    acao: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    descricao: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    data_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    dados_anteriores: Mapped[str | None] = mapped_column(
    Text,
    nullable=True
    )

    dados_posteriores: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )


