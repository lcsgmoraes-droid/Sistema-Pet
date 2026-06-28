"""Schemas das rotas de formas de pagamento e analise de venda."""

from typing import List, Optional

from pydantic import BaseModel


class FormaPagamentoTaxaCreate(BaseModel):
    forma_pagamento_id: int
    parcelas: int
    taxa_percentual: float
    descricao: Optional[str] = None


class FormaPagamentoTaxaResponse(BaseModel):
    id: int
    forma_pagamento_id: int
    parcelas: int
    taxa_percentual: float
    descricao: Optional[str]

    model_config = {"from_attributes": True}


class ItemAnaliseVenda(BaseModel):
    produto_id: int
    quantidade: float
    preco_venda: float
    custo: Optional[float] = None


class FormaPagamentoAnalise(BaseModel):
    forma_pagamento_id: int
    valor: float
    parcelas: int = 1


class AnaliseVendaRequest(BaseModel):
    items: List[ItemAnaliseVenda]
    desconto: float = 0
    taxa_entrega: float = 0
    formas_pagamento: List[FormaPagamentoAnalise] = []  # Múltiplas formas
    # Manter compatibilidade com código antigo
    forma_pagamento_id: Optional[int] = None
    parcelas: int = 1
    vendedor_id: Optional[int] = None


class AlertaAnalise(BaseModel):
    tipo: str  # "info", "warning", "error", "success"
    icone: str
    mensagem: str


class DetalhamentoComissao(BaseModel):
    produto: str
    percentual: float
    valor: float


class AnaliseVendaResponse(BaseModel):
    composicao: dict
    deducoes: dict
    resultado: dict
    alertas: List[AlertaAnalise]
    detalhamento_comissoes: List[DetalhamentoComissao]
    detalhamento_taxas: Optional[List[dict]] = []  # Detalhe de cada forma de pagamento
