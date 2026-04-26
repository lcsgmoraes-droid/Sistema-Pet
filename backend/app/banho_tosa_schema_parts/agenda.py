"""Schemas de agenda do Banho & Tosa."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class BanhoTosaAgendamentoServicoInput(BaseModel):
    servico_id: Optional[int] = None
    nome_servico: Optional[str] = Field(default=None, max_length=160)
    quantidade: Decimal = Field(default=Decimal("1"), gt=0)
    valor_unitario: Decimal = Field(default=Decimal("0"), ge=0)
    desconto: Decimal = Field(default=Decimal("0"), ge=0)
    tempo_previsto_minutos: Optional[int] = Field(default=None, ge=0, le=1440)


class BanhoTosaAgendamentoCreate(BaseModel):
    cliente_id: int = Field(..., gt=0)
    pet_id: int = Field(..., gt=0)
    data_hora_inicio: datetime
    data_hora_fim_prevista: Optional[datetime] = None
    profissional_principal_id: Optional[int] = None
    banhista_id: Optional[int] = None
    tosador_id: Optional[int] = None
    recurso_id: Optional[int] = Field(default=None, gt=0)
    origem: str = Field(default="balcao", max_length=30)
    observacoes: Optional[str] = None
    valor_previsto: Optional[Decimal] = Field(default=None, ge=0)
    servicos: List[BanhoTosaAgendamentoServicoInput] = Field(default_factory=list)


class BanhoTosaAgendamentoStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=40)
    observacoes: Optional[str] = None


class BanhoTosaAgendamentoServicoResponse(BaseModel):
    id: int
    servico_id: Optional[int] = None
    nome_servico_snapshot: str
    quantidade: Decimal
    valor_unitario: Decimal
    desconto: Decimal
    tempo_previsto_minutos: int

    class Config:
        from_attributes = True


class BanhoTosaAgendamentoResponse(BaseModel):
    id: int
    cliente_id: int
    cliente_nome: Optional[str] = None
    pet_id: int
    pet_nome: Optional[str] = None
    pet_especie: Optional[str] = None
    pet_porte: Optional[str] = None
    profissional_principal_id: Optional[int] = None
    banhista_id: Optional[int] = None
    tosador_id: Optional[int] = None
    recurso_id: Optional[int] = None
    recurso_nome: Optional[str] = None
    recurso_tipo: Optional[str] = None
    data_hora_inicio: datetime
    data_hora_fim_prevista: Optional[datetime] = None
    status: str
    origem: str
    observacoes: Optional[str] = None
    valor_previsto: Decimal
    taxi_dog_id: Optional[int] = None
    restricoes_veterinarias_snapshot: Optional[dict] = None
    perfil_comportamental_snapshot: Optional[dict] = None
    servicos: List[BanhoTosaAgendamentoServicoResponse] = Field(default_factory=list)


class BanhoTosaCapacidadeRecursoResponse(BaseModel):
    recurso_id: int
    recurso_nome: str
    recurso_tipo: str
    capacidade_simultanea: int
    agendamentos: int
    minutos_ocupados: int
    minutos_disponiveis: int
    ocupacao_percentual: float
    pico_simultaneo: int
    capacidade_excedida: bool


class BanhoTosaCapacidadeDiaResponse(BaseModel):
    data: date
    janela_inicio: str
    janela_fim: str
    total_agendamentos: int
    agendamentos_sem_recurso: int
    recursos: List[BanhoTosaCapacidadeRecursoResponse] = Field(default_factory=list)
    alertas: List[str] = Field(default_factory=list)


class BanhoTosaSlotSugestaoResponse(BaseModel):
    horario_inicio: datetime
    horario_fim: datetime
    recurso_id: int
    recurso_nome: str
    recurso_tipo: str
    capacidade_simultanea: int
    ocupacao_no_slot: int
    vagas_disponiveis: int
    motivo: str
