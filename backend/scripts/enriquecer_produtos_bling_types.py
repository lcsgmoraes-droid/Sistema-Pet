"""Tipos usados pelo enriquecimento de produtos via Bling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BlingRow:
    sku: str
    nome: str
    descricao_curta: str
    descricao_complementar: str
    marca: str
    fornecedor: str
    categoria: str
    departamento: str
    codigo_barras: str
    ncm: str
    cest: str
    origem: str
    perfil_tributario: str
    preco_custo: Optional[float]


@dataclass
class UpdateResult:
    sku: str
    produto_id: Optional[int]
    produto_nome: str
    acao: str
    detalhes: str


@dataclass
class FamilyDefaults:
    marca: str = ""
    fornecedor: str = ""
    categoria: str = ""
    departamento: str = ""
    descricao_curta: str = ""
    descricao_complementar: str = ""
    ncm: str = ""
    cest: str = ""
    origem: str = ""
    perfil_tributario: str = ""
