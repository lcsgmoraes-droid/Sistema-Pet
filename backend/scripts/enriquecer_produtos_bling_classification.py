"""Padroes familiares de classificacao para enriquecimento Bling."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Protocol, Tuple

from enriquecer_produtos_bling_types import BlingRow, FamilyDefaults
from enriquecer_produtos_bling_utils import build_family_key, normalize_text


class ExistingProdutoLike(Protocol):
    nome: str
    departamento_id: object | None
    categoria_id: object | None


def choose_most_common_text(values: Dict[str, int]) -> str:
    if not values:
        return ""
    return min(values.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))[0]


def choose_most_common_int(values: Dict[int, int]) -> Optional[int]:
    if not values:
        return None
    return min(values.items(), key=lambda item: (-item[1], item[0]))[0]


def build_family_defaults(rows: List[BlingRow]) -> Dict[str, FamilyDefaults]:
    counters: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    fields = [
        "marca",
        "fornecedor",
        "categoria",
        "departamento",
        "descricao_curta",
        "descricao_complementar",
        "ncm",
        "cest",
        "origem",
        "perfil_tributario",
    ]

    for row in rows:
        family_key = build_family_key(row.nome)
        if not family_key:
            continue
        for field in fields:
            value = normalize_text(getattr(row, field))
            if value:
                counters[family_key][field][value] += 1

    defaults: Dict[str, FamilyDefaults] = {}
    for family_key, field_counts in counters.items():
        defaults[family_key] = FamilyDefaults(
            marca=choose_most_common_text(field_counts["marca"]),
            fornecedor=choose_most_common_text(field_counts["fornecedor"]),
            categoria=choose_most_common_text(field_counts["categoria"]),
            departamento=choose_most_common_text(field_counts["departamento"]),
            descricao_curta=choose_most_common_text(field_counts["descricao_curta"]),
            descricao_complementar=choose_most_common_text(
                field_counts["descricao_complementar"]
            ),
            ncm=choose_most_common_text(field_counts["ncm"]),
            cest=choose_most_common_text(field_counts["cest"]),
            origem=choose_most_common_text(field_counts["origem"]),
            perfil_tributario=choose_most_common_text(
                field_counts["perfil_tributario"]
            ),
        )
    return defaults


def build_existing_classification_defaults(
    produtos: List[ExistingProdutoLike],
) -> Tuple[Dict[str, Optional[int]], Dict[str, Optional[int]]]:
    department_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
    category_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

    for produto in produtos:
        family_key = build_family_key(produto.nome)
        if not family_key:
            continue
        if produto.departamento_id:
            department_counts[family_key][int(produto.departamento_id)] += 1
        if produto.categoria_id:
            category_counts[family_key][int(produto.categoria_id)] += 1

    department_defaults = {
        family_key: choose_most_common_int(counts)
        for family_key, counts in department_counts.items()
    }
    category_defaults = {
        family_key: choose_most_common_int(counts)
        for family_key, counts in category_counts.items()
    }
    return department_defaults, category_defaults
