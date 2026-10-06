"""Schemas Pydantic usados pelas rotas de vendas."""

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class VendaItemSchema(BaseModel):
    item_id: Optional[int] = Field(default=None, gt=0)
    tipo: str
    produto_id: Optional[int] = None
    servico_descricao: Optional[str] = None
    quantidade: float
    preco_unitario: float
    desconto_item: Optional[float] = 0
    subtotal: float
    lote_id: Optional[int] = None
    pet_id: Optional[int] = None
    protocolo_recorrencia_id: Optional[int] = None
    ignorar_recorrencia: bool = False
    is_kit: Optional[bool] = None
    racao_data_prevista_fim: Optional[date] = None
    racao_prazo_estimado_dias: Optional[int] = Field(default=None, ge=1, le=365)

    @model_validator(mode="after")
    def validar_previsao_fim_racao(self):
        if self.racao_data_prevista_fim and self.racao_prazo_estimado_dias:
            raise ValueError(
                "Informe a data ou o prazo para a ração acabar, não os dois."
            )
        if (
            self.racao_data_prevista_fim
            and self.racao_data_prevista_fim <= date.today()
        ):
            raise ValueError("A data prevista precisa ser posterior a hoje.")
        return self


class VendaPagamentoSchema(BaseModel):
    forma_pagamento: str
    forma_pagamento_id: Optional[int] = None
    valor: float
    bandeira: Optional[str] = None
    numero_parcelas: Optional[int] = Field(default=1, ge=1, le=60)
    numero_transacao: Optional[str] = None
    numero_autorizacao: Optional[str] = None
    nsu_cartao: Optional[str] = None
    operadora_id: Optional[int] = None
    modalidade_cartao: Optional[str] = None
    valor_recebido: Optional[float] = None
    troco: Optional[float] = None
    data_recebimento_prevista: Optional[date] = None
    intervalo_crediario: Optional[Literal["7_dias", "15_dias", "mensal"]] = None


class CriarVendaRequest(BaseModel):
    caixa_revisao_id: Optional[int] = None
    data_ocorrencia: Optional[datetime] = None
    motivo_revisao: Optional[str] = None
    cliente_id: Optional[int] = None
    vendedor_id: Optional[int] = None
    funcionario_id: Optional[int] = None
    vendedor_funcionario_id: Optional[int] = None
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
    pagamento_entrega_previsto: Optional[dict] = None


class FinalizarVendaRequest(BaseModel):
    caixa_revisao_id: Optional[int] = None
    data_ocorrencia: Optional[datetime] = None
    motivo_revisao: Optional[str] = None
    pagamentos: List[VendaPagamentoSchema]
    cupom_code: Optional[str] = None
    cupom_discount_applied: Optional[float] = None
    motivo_liberacao_crediario: Optional[str] = Field(default=None, max_length=500)
    nao_gerar_beneficios: bool = False
    justificativa_nao_gerar_beneficios: Optional[str] = Field(
        default=None, max_length=500
    )


class CancelarVendaRequest(BaseModel):
    motivo: Optional[str] = None


class ExcluirVendaRequest(BaseModel):
    motivo: Optional[str] = None
    justificativa: Optional[str] = None


class MarcarEntregueRequest(BaseModel):
    retirado_por: str | None = None
