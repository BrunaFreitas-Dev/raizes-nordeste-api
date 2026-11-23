
from enum import Enum


class CanalPedido(str, Enum):
    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"
    WEB = "WEB"


class StatusPedido(str, Enum):
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    FALHA_PAGAMENTO = "FALHA_PAGAMENTO"
    PAGO = "PAGO"
    PRONTO_PARA_RETIRADA = "PRONTO_PARA_RETIRADA"
    CANCELADO = "CANCELADO"
