"""Schemas operacionais, insumos e custos do Banho & Tosa."""

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class BanhoTosaAtendimentoStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=40)
    observacoes_saida: Optional[str] = None


class BanhoTosaEtapaCreate(BaseModel):
    tipo: str = Field(..., min_length=1, max_length=40)
    responsavel_id: Optional[int] = None
    recurso_id: Optional[int] = None
    observacoes: Optional[str] = None


class BanhoTosaEtapaUpdate(BaseModel):
    responsavel_id: Optional[int] = None
    recurso_id: Optional[int] = None
    observacoes: Optional[str] = None


class BanhoTosaEtapaFinalizarInput(BaseModel):
    observacoes: Optional[str] = None


class BanhoTosaEtapaResponse(BaseModel):
    id: int
    atendimento_id: int
    tipo: str
    responsavel_id: Optional[int] = None
    responsavel_nome: Optional[str] = None
    recurso_id: Optional[int] = None
    recurso_nome: Optional[str] = None
    inicio_em: Optional[datetime] = None
    fim_em: Optional[datetime] = None
    duracao_minutos: Optional[int] = None
    observacoes: Optional[str] = None


class BanhoTosaAtendimentoResponse(BaseModel):
    id: int
    agendamento_id: Optional[int] = None
    cliente_id: int
    cliente_nome: Optional[str] = None
    pet_id: int
    pet_nome: Optional[str] = None
    pet_especie: Optional[str] = None
    pet_porte: Optional[str] = None
    status: str
    checkin_em: Optional[datetime] = None
    inicio_em: Optional[datetime] = None
    fim_em: Optional[datetime] = None
    entregue_em: Optional[datetime] = None
    porte_snapshot: Optional[str] = None
    pelagem_snapshot: Optional[str] = None
    observacoes_entrada: Optional[str] = None
    observacoes_saida: Optional[str] = None
    restricoes_veterinarias_snapshot: Optional[dict] = None
    perfil_comportamental_snapshot: Optional[dict] = None
    ocorrencias: Optional[List[dict]] = None
    venda_id: Optional[int] = None
    venda_numero: Optional[str] = None
    venda_status: Optional[str] = None
    venda_total: Optional[Decimal] = None
    venda_total_pago: Optional[Decimal] = None
    venda_valor_restante: Optional[Decimal] = None
    venda_status_pagamento: Optional[str] = None
    conta_receber_id: Optional[int] = None
    pacote_credito_id: Optional[int] = None
    pacote_movimento_id: Optional[int] = None
    pacote_nome: Optional[str] = None
    pacote_saldo_creditos: Optional[Decimal] = None
    fechamento_alertas: List[str] = Field(default_factory=list)
    pdv_url: Optional[str] = None
    etapas: List[BanhoTosaEtapaResponse] = Field(default_factory=list)


class BanhoTosaOcorrenciaCreate(BaseModel):
    tipo: str = Field(default="observacao", min_length=1, max_length=40)
    gravidade: str = Field(default="baixa", min_length=1, max_length=20)
    descricao: str = Field(..., min_length=1)
    responsavel_id: Optional[int] = None


class BanhoTosaFotoCreate(BaseModel):
    tipo: str = Field(default="entrada", min_length=1, max_length=30)
    url: str = Field(..., min_length=1, max_length=500)
    descricao: Optional[str] = None


class BanhoTosaFotoResponse(BaseModel):
    id: int
    atendimento_id: int
    tipo: str
    url: str
    thumbnail_url: Optional[str] = None
    descricao: Optional[str] = None
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class BanhoTosaInsumoUsadoCreate(BaseModel):
    produto_id: int = Field(..., gt=0)
    quantidade_usada: Decimal = Field(default=Decimal("0"), ge=0)
    quantidade_desperdicio: Decimal = Field(default=Decimal("0"), ge=0)
    custo_unitario_snapshot: Optional[Decimal] = Field(default=None, ge=0)
    responsavel_id: Optional[int] = None
    baixar_estoque: bool = False


class BanhoTosaInsumoUsadoUpdate(BaseModel):
    quantidade_usada: Optional[Decimal] = Field(default=None, ge=0)
    quantidade_desperdicio: Optional[Decimal] = Field(default=None, ge=0)
    custo_unitario_snapshot: Optional[Decimal] = Field(default=None, ge=0)
    responsavel_id: Optional[int] = None


class BanhoTosaInsumoUsadoResponse(BaseModel):
    id: int
    atendimento_id: int
    produto_id: int
    produto_nome: Optional[str] = None
    produto_codigo: Optional[str] = None
    unidade: Optional[str] = None
    quantidade_prevista: Decimal
    quantidade_usada: Decimal
    quantidade_desperdicio: Decimal
    custo_unitario_snapshot: Decimal
    custo_total: Decimal
    movimentacao_estoque_id: Optional[int] = None
    movimentacao_estorno_id: Optional[int] = None
    estoque_estornado_em: Optional[datetime] = None
    responsavel_id: Optional[int] = None
    responsavel_nome: Optional[str] = None


class BanhoTosaInsumoCustoInput(BaseModel):
    quantidade_usada: Decimal = Field(default=Decimal("0"), ge=0)
    quantidade_desperdicio: Decimal = Field(default=Decimal("0"), ge=0)
    custo_unitario_snapshot: Decimal = Field(default=Decimal("0"), ge=0)


class BanhoTosaAguaCustoInput(BaseModel):
    custo_litro_agua: Decimal = Field(default=Decimal("0"), ge=0)
    vazao_chuveiro_litros_min: Optional[Decimal] = Field(default=None, ge=0)
    minutos_banho: Optional[Decimal] = Field(default=None, ge=0)
    litros_usados: Optional[Decimal] = Field(default=None, ge=0)
    agua_padrao_litros: Optional[Decimal] = Field(default=None, ge=0)


class BanhoTosaEquipamentoUsoInput(BaseModel):
    potencia_watts: Decimal = Field(default=Decimal("0"), ge=0)
    minutos_uso: Decimal = Field(default=Decimal("0"), ge=0)
    custo_kwh: Decimal = Field(default=Decimal("0"), ge=0)
    custo_manutencao_hora: Decimal = Field(default=Decimal("0"), ge=0)
    kwh_real: Optional[Decimal] = Field(default=None, ge=0)


class BanhoTosaMaoObraInput(BaseModel):
    custo_mensal_funcionario: Decimal = Field(default=Decimal("0"), ge=0)
    horas_produtivas_mes: Decimal = Field(default=Decimal("0"), ge=0)
    minutos_trabalhados: Decimal = Field(default=Decimal("0"), ge=0)


class BanhoTosaComissaoInput(BaseModel):
    modelo: Literal["nenhum", "percentual_valor", "valor_fixo", "percentual_margem"] = "nenhum"
    valor_base: Decimal = Field(default=Decimal("0"), ge=0)
    percentual: Decimal = Field(default=Decimal("0"), ge=0)
    valor_fixo: Decimal = Field(default=Decimal("0"), ge=0)


class BanhoTosaTaxiDogInput(BaseModel):
    km_real: Decimal = Field(default=Decimal("0"), ge=0)
    custo_km: Decimal = Field(default=Decimal("0"), ge=0)
    custo_motorista: Decimal = Field(default=Decimal("0"), ge=0)
    rateio_manutencao: Decimal = Field(default=Decimal("0"), ge=0)
    custo_real_informado: Optional[Decimal] = Field(default=None, ge=0)


class BanhoTosaCustoSimulacaoInput(BaseModel):
    valor_cobrado: Decimal = Field(default=Decimal("0"), ge=0)
    insumos: List[BanhoTosaInsumoCustoInput] = Field(default_factory=list)
    agua: BanhoTosaAguaCustoInput = Field(default_factory=BanhoTosaAguaCustoInput)
    energia: List[BanhoTosaEquipamentoUsoInput] = Field(default_factory=list)
    mao_obra: List[BanhoTosaMaoObraInput] = Field(default_factory=list)
    comissao: BanhoTosaComissaoInput = Field(default_factory=BanhoTosaComissaoInput)
    taxi_dog: BanhoTosaTaxiDogInput = Field(default_factory=BanhoTosaTaxiDogInput)
    custo_taxas_pagamento: Decimal = Field(default=Decimal("0"), ge=0)
    custo_rateio_operacional: Decimal = Field(default=Decimal("0"), ge=0)


class BanhoTosaCustoSnapshotResponse(BaseModel):
    valor_cobrado: Decimal
    custo_insumos: Decimal
    custo_agua: Decimal
    custo_energia: Decimal
    custo_mao_obra: Decimal
    custo_comissao: Decimal
    custo_taxi_dog: Decimal
    custo_taxas_pagamento: Decimal
    custo_rateio_operacional: Decimal
    custo_total: Decimal
    margem_valor: Decimal
    margem_percentual: Decimal


class BanhoTosaCustoAtendimentoResponse(BanhoTosaCustoSnapshotResponse):
    id: Optional[int] = None
    atendimento_id: int
    detalhes_json: Optional[dict] = None


class BanhoTosaDashboardResponse(BaseModel):
    data_referencia: datetime
    agendamentos_abertos: int
    atendimentos_em_execucao: int
    atendimentos_prontos: int
    atendimentos_prontos_sem_venda: int = 0
    cobrancas_pendentes: int = 0
    atendimentos_entregues: int
    servicos_ativos: int
    recursos_ativos: int
    avaliacoes_hoje: int = 0
    nps_hoje: Decimal = Decimal("0")
