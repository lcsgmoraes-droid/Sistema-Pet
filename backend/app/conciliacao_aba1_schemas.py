"""Schemas da conciliacao de vendas PDV vs Stone."""

from typing import List

from pydantic import BaseModel


class ConfirmarMatchRequest(BaseModel):
    """Confirmar match entre venda PDV e NSU Stone"""

    venda_id: int
    nsu_stone: str
    aplicar_correcoes: bool = False  # Se True, atualiza dados do PDV com dados da Stone


class CorrigirDivergenciaRequest(BaseModel):
    """Corrigir divergência manualmente"""

    venda_id: int
    nsu_stone: str
    campo: str  # "parcelas", "bandeira", "valor"
    novo_valor: str
    motivo: str


class ConfirmarMatchesRequest(BaseModel):
    importacao_id: int
    matches_confirmados: List[dict]


class AtualizarOperadoraRequest(BaseModel):
    pagamento_id: int
    operadora_id: int
