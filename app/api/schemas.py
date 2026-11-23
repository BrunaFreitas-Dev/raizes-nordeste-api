
from app.domain.enums import CanalPedido

from datetime import datetime
from decimal import Decimal
from enum import Enum

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


class UnidadeResposta(BaseModel):
    id_unidade: int
    nome: str
    endereco: str
    cidade: str
    estado: str
    telefone: str
    regiao: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class ItemCardapioResposta(BaseModel):
    id_produto: int
    nome: str
    descricao: str | None
    categoria: str | None
    preco: Decimal
    disponivel: bool


class EntradaEstoque(BaseModel):
    quantidade: int = Field(gt=0)
    observacao: str | None = None


class ItemPedidoEntrada(BaseModel):
    id_produto_unidade: int
    quantidade: int = Field(gt=0)


class PedidoCriacao(BaseModel):
    id_unidade: int
    canal_pedido: CanalPedido = Field(alias="canalPedido")
    itens: list[ItemPedidoEntrada] = Field(min_length=1)

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True
    )


class ItemPedidoResposta(BaseModel):
    id_produto_unidade: int
    quantidade: int
    preco_unitario: Decimal
    subtotal: Decimal


class PedidoResposta(BaseModel):
    id_pedido: int
    id_unidade: int
    canal_pedido: CanalPedido
    status_pedido: str
    valor_total: Decimal
    data_pedido: datetime
    data_limite_pagamento: datetime
    codigo_acompanhamento: str

    model_config = ConfigDict(from_attributes=True)



class PedidoConsultaResposta(BaseModel):
    id_pedido: int
    id_unidade: int
    canal_pedido: CanalPedido
    status_pedido: str
    valor_total: Decimal
    data_pedido: datetime
    data_limite_pagamento: datetime

    model_config = ConfigDict(from_attributes=True)


class PedidoDetalheResposta(PedidoConsultaResposta):
    itens: list[ItemPedidoResposta]



class ResultadoPagamentoMock(str, Enum):
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"


class PagamentoEntrada(BaseModel):
    forma_pagamento: str = Field(min_length=1, max_length=30)
    resultado_simulado: ResultadoPagamentoMock



class CancelamentoPedidoEntrada(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)

    model_config = ConfigDict(extra="forbid")


class AtualizacaoStatusPedidoEntrada(BaseModel):
    observacao: str | None = Field(
        default=None,
        max_length=255,
    )

    model_config = ConfigDict(extra="forbid")
