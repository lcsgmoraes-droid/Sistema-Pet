"""Schemas dos relatorios operacionais do Banho & Tosa."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class BanhoTosaRelatorioResumo(BaseModel):
    atendimentos: int
    agendamentos: int
    receita: Decimal
    custo_total: Decimal
    margem_valor: Decimal
    margem_percentual: Decimal
    ticket_medio: Decimal
    desperdicio_valor: Decimal
    desperdicio_quantidade: Decimal
    ocupacao_media_percentual: Decimal
    avaliacoes: int = 0
    nps: Decimal = Decimal("0")
    promotores: int = 0
    neutros: int = 0
    detratores: int = 0
    nota_servico_media: Decimal = Decimal("0")


class BanhoTosaRelatorioMargemItem(BaseModel):
    chave: str
    nome: str
    atendimentos: int
    receita: Decimal
    custo_total: Decimal
    margem_valor: Decimal
    margem_percentual: Decimal


class BanhoTosaRelatorioProdutividadeItem(BaseModel):
    responsavel_id: int
    responsavel_nome: str
    etapas: int
    atendimentos: int
    minutos_trabalhados: int
    horas_trabalhadas: Decimal


class BanhoTosaRelatorioOcupacaoItem(BaseModel):
    recurso_id: int
    recurso_nome: str
    recurso_tipo: str
    capacidade_simultanea: int
    minutos_ocupados: int
    minutos_disponiveis: int
    ocupacao_percentual: Decimal


class BanhoTosaRelatorioDesperdicioItem(BaseModel):
    produto_id: int
    produto_nome: str
    unidade: Optional[str] = None
    quantidade_desperdicio: Decimal
    custo_desperdicio: Decimal


class BanhoTosaRelatorioOperacionalResponse(BaseModel):
    data_inicio: date
    data_fim: date
    resumo: BanhoTosaRelatorioResumo
    margem_por_servico: list[BanhoTosaRelatorioMargemItem] = Field(default_factory=list)
    margem_por_porte: list[BanhoTosaRelatorioMargemItem] = Field(default_factory=list)
    produtividade: list[BanhoTosaRelatorioProdutividadeItem] = Field(default_factory=list)
    ocupacao_recursos: list[BanhoTosaRelatorioOcupacaoItem] = Field(default_factory=list)
    desperdicios: list[BanhoTosaRelatorioDesperdicioItem] = Field(default_factory=list)
    alertas: list[str] = Field(default_factory=list)
