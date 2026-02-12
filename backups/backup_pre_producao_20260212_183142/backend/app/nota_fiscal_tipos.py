
from enum import Enum

class TipoNotaFiscal(str, Enum):
    LOJA_FISICA = "loja_fisica"
    ONLINE = "online"
    MISTA = "mista"

    @classmethod
    def valores(cls):
        return [t.value for t in cls]
