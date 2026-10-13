"""Schemas das rotas de formas de pagamento e analise de venda."""

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.services.venda_descontos import moeda, normalizar_item_venda


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
    desconto_item: float = Field(default=0, ge=0)
    custo: Optional[float] = None


class FormaPagamentoAnalise(BaseModel):
    forma_pagamento_id: int
    valor: float
    parcelas: int = 1
    operadora_id: Optional[int] = None
    bandeira: Optional[str] = None
    modalidade: Optional[str] = None


class AnaliseVendaRequest(BaseModel):
    items: List[ItemAnaliseVenda]
    desconto: float = 0
    desconto_venda_valor: Optional[float] = Field(default=None, ge=0)
    cupom_discount_applied: Optional[float] = Field(default=None, ge=0)
    taxa_entrega: float = 0
    formas_pagamento: List[FormaPagamentoAnalise] = []  # Múltiplas formas
    # Manter compatibilidade com código antigo
    forma_pagamento_id: Optional[int] = None
    parcelas: int = 1
    vendedor_id: Optional[int] = None

    @model_validator(mode="after")
    def normalizar_precisao_descontos_separados(self):
        if self.desconto_venda_valor is not None:
            self.desconto_venda_valor = float(moeda(self.desconto_venda_valor))
            if self.cupom_discount_applied is not None:
                self.cupom_discount_applied = float(moeda(self.cupom_discount_applied))
            for item in self.items:
                normalizado = normalizar_item_venda(
                    {
                        "quantidade": item.quantidade,
                        "preco_unitario": item.preco_venda,
                        "desconto_item": item.desconto_item,
                    }
                )
                item.quantidade = normalizado["quantidade"]
                item.preco_venda = normalizado["preco_unitario"]
                item.desconto_item = normalizado["desconto_item"]
        return self


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
