
from enum import Enum

class CanalVenda(str, Enum):
    LOJA_FISICA = "loja_fisica"
    ONLINE = "online"
    MERCADO_LIVRE = "mercado_livre"
    SHOPEE = "shopee"
    AMAZON = "amazon"

    @classmethod
    def valores(cls):
        return [c.value for c in cls]
