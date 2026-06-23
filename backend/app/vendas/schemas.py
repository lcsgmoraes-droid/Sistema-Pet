"""Schemas Pydantic usados pelas rotas de vendas."""

from typing import List, Optional

from pydantic import BaseModel


class VendaItemSchema(BaseModel):
    tipo: str
    produto_id: Optional[int] = None
    servico_descricao: Optional[str] = None
    quantidade: float
    preco_unitario: float
    desconto_item: Optional[float] = 0
    subtotal: float
    lote_id: Optional[int] = None
    pet_id: Optional[int] = None
    is_kit: Optional[bool] = None


class VendaPagamentoSchema(BaseModel):
    forma_pagamento: str
    valor: float
    bandeira: Optional[str] = None
    numero_parcelas: Optional[int] = 1
    numero_transacao: Optional[str] = None
    numero_autorizacao: Optional[str] = None
    nsu_cartao: Optional[str] = None
    operadora_id: Optional[int] = None
    valor_recebido: Optional[float] = None
    troco: Optional[float] = None


class CriarVendaRequest(BaseModel):
    cliente_id: Optional[int] = None
    vendedor_id: Optional[int] = None
    funcionario_id: Optional[int] = None
    itens: List[VendaItemSchema]
    desconto_valor: Optional[float] = 0
    desconto_percentual: Optional[float] = 0
    cupom_code: Optional[str] = None
    cupom_discount_applied: Optional[float] = None
    observacoes: Optional[str] = None
    tem_entrega: bool = False
    taxa_entrega: Optional[float] = 0
    percentual_taxa_loja: Optional[float] = 100
    percentual_taxa_entregador: Optional[float] = 0
    entregador_id: Optional[int] = None
    loja_origem: Optional[str] = None
    endereco_entrega: Optional[str] = None
    distancia_km: Optional[float] = None
    valor_por_km: Optional[float] = None
    observacoes_entrega: Optional[str] = None


class FinalizarVendaRequest(BaseModel):
    pagamentos: List[VendaPagamentoSchema]
    cupom_code: Optional[str] = None
    cupom_discount_applied: Optional[float] = None


class CancelarVendaRequest(BaseModel):
    motivo: Optional[str] = None


class ExcluirVendaRequest(BaseModel):
    motivo: Optional[str] = None
    justificativa: Optional[str] = None


class MarcarEntregueRequest(BaseModel):
    retirado_por: str | None = None
