"""Schemas das sugestoes inteligentes de racoes."""

from typing import Any

from pydantic import BaseModel


class DuplicataDetectada(BaseModel):
    produto_1: dict[str, Any]
    produto_2: dict[str, Any]
    score_similaridade: float
    razoes: list[str]
    sugestao_acao: str


class PadronizacaoNome(BaseModel):
    produto_id: int
    nome_atual: str
    nome_sugerido: str
    razao: str
    confianca: float


class GapEstoque(BaseModel):
    segmento_tipo: str
    segmento_valor: str
    total_produtos: int
    produtos_sem_estoque: int
    percentual_sem_estoque: float
    importancia: str
    faturamento_historico: float
    sugestao: str


__all__ = ["DuplicataDetectada", "GapEstoque", "PadronizacaoNome"]
