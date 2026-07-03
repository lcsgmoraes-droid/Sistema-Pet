#!/usr/bin/env python
# ruff: noqa: F401

"""Enriquece produtos do Sistema Pet com dados do Bling por SKU.

Regra importante (pedido do usuario):
- NUNCA atualiza preco_venda
- Atualiza apenas preco_custo e demais metadados

Fontes:
- CSV de produtos do Bling (dados fiscais, marca, fornecedor, categoria, departamento etc)
- CSV de estrutura/composicao (custo de kits: quantidade * custo unitario)

Fluxo recomendado:
1) Rodar preview (sem --apply)
2) Validar relatorios em backend/reports/enriquecimento_bling
3) Rodar com --apply em DEV (amostra)
4) Validar
"""

from __future__ import annotations

import argparse

from enriquecer_produtos_bling_classification import (
    build_existing_classification_defaults,
    build_family_defaults,
    choose_most_common_int,
    choose_most_common_text,
)
from enriquecer_produtos_bling_loaders import load_bling_rows, load_kit_costs
from enriquecer_produtos_bling_processing import run
from enriquecer_produtos_bling_types import BlingRow, FamilyDefaults, UpdateResult
from enriquecer_produtos_bling_utils import (
    build_family_key,
    map_origem,
    normalize_key,
    normalize_text,
    only_digits,
    parse_decimal,
    pick,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enriquecer produtos por SKU a partir do Bling"
    )
    parser.add_argument(
        "--bling-csv",
        type=str,
        default="PRODUTOS BLING/produtos_2026-03-18-17-11-13.csv",
        help="CSV de produtos exportado do Bling",
    )
    parser.add_argument(
        "--estrutura-csv",
        type=str,
        default="PRODUTOS BLING/produtos_estrutura_2026-03-18-17-09-07.csv",
        help="CSV de estrutura/composicao para custo de kit",
    )
    parser.add_argument("--tenant-id", type=str, default="", help="Tenant alvo")
    parser.add_argument(
        "--apply", action="store_true", help="Aplica alteracoes no banco"
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=0,
        help="Limita aplicacao a N produtos (somente com --apply)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="backend/reports/enriquecimento_bling",
        help="Pasta de saida dos relatorios",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
