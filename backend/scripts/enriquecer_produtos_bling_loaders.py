"""Carregadores CSV do enriquecimento Bling."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

from enriquecer_produtos_bling_types import BlingRow
from enriquecer_produtos_bling_utils import (
    normalize_key,
    normalize_text,
    parse_decimal,
    pick,
)


def _validated_csv_path(csv_path: Path, allowed_root: Optional[Path]) -> Path:
    safe_path = csv_path.resolve(strict=True)
    if allowed_root is not None:
        safe_path.relative_to(allowed_root.resolve())
    return safe_path


def load_bling_rows(
    csv_path: Path, allowed_root: Optional[Path] = None
) -> List[BlingRow]:
    rows: List[BlingRow] = []
    safe_path = _validated_csv_path(csv_path, allowed_root)
    with safe_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for raw in reader:
            sku = pick(raw, ["Código", "Codigo", "codigo"])
            if not normalize_key(sku):
                continue
            rows.append(
                BlingRow(
                    sku=sku,
                    nome=pick(raw, ["Descrição", "Descricao", "descricao"]),
                    descricao_curta=pick(raw, ["Descrição Curta", "Descricao Curta"]),
                    descricao_complementar=pick(
                        raw,
                        [
                            "Descrição Complementar",
                            "Descricao Complementar",
                            "Observações",
                            "Observacoes",
                        ],
                    ),
                    marca=pick(raw, ["Marca", "marca"]),
                    fornecedor=pick(raw, ["Fornecedor", "fornecedor"]),
                    categoria=pick(
                        raw,
                        ["Categoria do produto", "Grupo de produtos", "Grupo", "grupo"],
                    ),
                    departamento=pick(raw, ["Departamento", "departamento"]),
                    codigo_barras=pick(
                        raw,
                        ["GTIN/EAN", "Código Barra", "Codigo Barra", "codigo_barras"],
                    ),
                    ncm=pick(raw, ["NCM", "Código NCM", "Codigo NCM"]),
                    cest=pick(raw, ["CEST"]),
                    origem=pick(raw, ["Origem", "Origem da mercadoria"]),
                    perfil_tributario=pick(
                        raw, ["Tributos", "Perfil Tributário", "Perfil Tributario"]
                    ),
                    preco_custo=(
                        parse_decimal(
                            pick(
                                raw,
                                [
                                    "Preço de custo",
                                    "Preco de custo",
                                    "Preço de Compra",
                                    "Preco de Compra",
                                    "Custo",
                                ],
                            )
                        )
                    ),
                )
            )
    return rows


def load_kit_costs(
    csv_path: Optional[Path], allowed_root: Optional[Path] = None
) -> Dict[str, float]:
    if not csv_path or not csv_path.exists():
        return {}

    costs: Dict[str, float] = {}
    safe_path = _validated_csv_path(csv_path, allowed_root)
    with safe_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for raw in reader:
            comp_code = normalize_text(raw.get("Código da composição"))
            if not normalize_key(comp_code):
                continue

            qty = parse_decimal(raw.get("Quantidade do Componente"))
            unit_cost = parse_decimal(raw.get("Custo unitário"))
            if qty is None or unit_cost is None:
                continue

            key = normalize_key(comp_code)
            costs[key] = costs.get(key, 0.0) + (qty * unit_cost)

    return costs
