"""Schemas da baixa FULL por NF."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class SaidaFullNFItemRequest(BaseModel):
    """Item para baixa de estoque por NF de saida."""

    produto_id: Optional[int] = None
    sku: Optional[str] = None
    quantidade: float = Field(gt=0)


class SaidaFullNFRequest(BaseModel):
    """Baixa em lote de estoque vinculada a uma NF de saida."""

    numero_nf: str
    plataforma: Optional[str] = None
    observacao: Optional[str] = None
    permitir_estoque_negativo: bool = False
    tarifa_envio: Optional[float] = 0
    categoria_tarifa_id: Optional[int] = None
    dre_subcategoria_tarifa_id: Optional[int] = None
    data_vencimento_tarifa: Optional[date] = None
    itens: List[SaidaFullNFItemRequest]


class SaidaFullNFCanalUpdateRequest(BaseModel):
    """Atualizacao do canal/origem de uma baixa FULL ja processada."""

    plataforma: str
