"""Accounting category setup for the operational demo seed."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.scripts.seed_demo_operacional_db import _scalar


def _ensure_dre_subcategory(
    db,
    *,
    tenant_id: str,
    category_name: str,
    category_nature: str,
    category_order: int,
    sub_name: str,
    tipo_custo: str,
    base_rateio: str | None,
    custo_pe: str | None,
) -> int:
    category_id = _scalar(
        db,
        """
        SELECT id FROM dre_categorias
        WHERE tenant_id = :tenant_id AND nome = :name
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "name": category_name},
    )
    if not category_id:
        category_id = _scalar(
            db,
            """
            INSERT INTO dre_categorias (
                nome, ordem, natureza, ativo, tenant_id, created_at, updated_at
            )
            VALUES (
                :name, :ordem, :natureza, true, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "name": category_name,
                "ordem": category_order,
                "natureza": category_nature,
                "tenant_id": tenant_id,
            },
        )

    sub_id = _scalar(
        db,
        """
        SELECT id FROM dre_subcategorias
        WHERE tenant_id = :tenant_id AND nome = :name
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "name": sub_name},
    )
    if sub_id:
        db.execute(
            text(
                """
                UPDATE dre_subcategorias
                SET categoria_id = :category_id,
                    tipo_custo = :tipo_custo,
                    base_rateio = :base_rateio,
                    escopo_rateio = 'AMBOS',
                    custo_pe = :custo_pe,
                    ativo = true,
                    updated_at = now()
                WHERE id = :sub_id
                """
            ),
            {
                "category_id": category_id,
                "tipo_custo": tipo_custo,
                "base_rateio": base_rateio,
                "custo_pe": custo_pe,
                "sub_id": sub_id,
            },
        )
        return int(sub_id)

    return int(
        _scalar(
            db,
            """
            INSERT INTO dre_subcategorias (
                categoria_id, nome, tipo_custo, base_rateio, escopo_rateio,
                ativo, custo_pe, tenant_id, created_at, updated_at
            )
            VALUES (
                :category_id, :name, :tipo_custo, :base_rateio, 'AMBOS',
                true, :custo_pe, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "category_id": category_id,
                "name": sub_name,
                "tipo_custo": tipo_custo,
                "base_rateio": base_rateio,
                "custo_pe": custo_pe,
                "tenant_id": tenant_id,
            },
        )
    )


def _ensure_financial_category(
    db,
    *,
    tenant_id: str,
    user_id: int,
    name: str,
    tipo: str,
    dre_subcategory_id: int | None,
    tipo_custo: str | None = None,
    color: str = "#2563EB",
    icon: str = "tag",
) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM categorias_financeiras
        WHERE tenant_id = :tenant_id AND lower(nome) = lower(:name)
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "name": name},
    )
    if existing:
        db.execute(
            text(
                """
                UPDATE categorias_financeiras
                SET tipo = :tipo,
                    dre_subcategoria_id = :dre_subcategory_id,
                    tipo_custo = :tipo_custo,
                    ativo = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "id": existing,
                "tipo": tipo,
                "dre_subcategory_id": dre_subcategory_id,
                "tipo_custo": tipo_custo,
            },
        )
        return int(existing)

    return int(
        _scalar(
            db,
            """
            INSERT INTO categorias_financeiras (
                nome, tipo, cor, icone, descricao, ativo, dre_subcategoria_id,
                tipo_custo, user_id, tenant_id, created_at, updated_at
            )
            VALUES (
                :name, :tipo, :color, :icon, :description, true,
                :dre_subcategory_id, :tipo_custo, :user_id, :tenant_id,
                now(), now()
            )
            RETURNING id
            """,
            {
                "name": name,
                "tipo": tipo,
                "color": color,
                "icon": icon,
                "description": "Cadastro demo operacional",
                "dre_subcategory_id": dre_subcategory_id,
                "tipo_custo": tipo_custo,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )


def _ensure_accounting_setup(
    db, *, tenant_id: str, user_id: int
) -> dict[str, dict[str, Any]]:
    dre_specs = {
        "receita_produtos": (
            "Receitas de Vendas",
            "receita",
            1,
            "Vendas de Produtos",
            "DIRETO",
            None,
            "variavel",
        ),
        "receita_app": (
            "Receitas de Vendas",
            "receita",
            1,
            "Vendas App",
            "DIRETO",
            None,
            "variavel",
        ),
        "receita_ecommerce": (
            "Receitas de Vendas",
            "receita",
            1,
            "Vendas Ecommerce",
            "DIRETO",
            None,
            "variavel",
        ),
        "descontos": (
            "Deducoes da Receita",
            "despesa",
            3,
            "Descontos Concedidos",
            "DIRETO",
            None,
            "variavel",
        ),
        "cmv": (
            "Custo das Mercadorias Vendidas",
            "custo",
            4,
            "CMV - Produtos",
            "DIRETO",
            None,
            "variavel",
        ),
        "taxas_cartao": (
            "Custos Diretos de Venda",
            "custo",
            5,
            "Taxas de Cartao",
            "DIRETO",
            None,
            "variavel",
        ),
        "comissoes_vendas": (
            "Custos Diretos de Venda",
            "custo",
            5,
            "Comissoes de Vendas",
            "DIRETO",
            None,
            "variavel",
        ),
        "frete_vendas": (
            "Custos Diretos de Venda",
            "custo",
            5,
            "Fretes sobre Vendas",
            "DIRETO",
            None,
            "variavel",
        ),
        "repasse_entrega": (
            "Custos Diretos de Venda",
            "custo",
            5,
            "Repasse Entregador",
            "DIRETO",
            None,
            "variavel",
        ),
        "compra_mercadorias": (
            "Custo das Mercadorias Vendidas",
            "custo",
            4,
            "Compra de Mercadorias",
            "DIRETO",
            None,
            "variavel",
        ),
        "folha_operacional": (
            "Despesas com Pessoal",
            "despesa",
            6,
            "Folha - Operacional",
            "INDIRETO_RATEAVEL",
            "FATURAMENTO",
            "fixo",
        ),
        "aluguel_loja": (
            "Despesas de Ocupacao",
            "despesa",
            7,
            "Aluguel - Loja",
            "INDIRETO_RATEAVEL",
            "FATURAMENTO",
            "fixo",
        ),
        "energia": (
            "Despesas de Ocupacao",
            "despesa",
            7,
            "Energia Eletrica",
            "INDIRETO_RATEAVEL",
            "FATURAMENTO",
            "fixo",
        ),
        "marketing": (
            "Despesas Comerciais",
            "despesa",
            8,
            "Marketing Digital",
            "INDIRETO_RATEAVEL",
            "FATURAMENTO",
            "fixo",
        ),
        "impostos": (
            "Tributos sobre Vendas",
            "despesa",
            11,
            "Simples Nacional",
            "DIRETO",
            None,
            "variavel",
        ),
    }

    category_specs = {
        "receita_produtos": (
            "Receitas de Vendas",
            "receita",
            "#059669",
            "shopping-cart",
        ),
        "receita_app": ("Vendas App", "receita", "#0F766E", "smartphone"),
        "receita_ecommerce": ("Vendas Ecommerce", "receita", "#2563EB", "globe"),
        "descontos": ("Descontos Concedidos", "despesa", "#EA580C", "badge-percent"),
        "cmv": ("CMV", "despesa", "#475569", "package"),
        "taxas_cartao": ("Taxas de Cartao", "despesa", "#7C3AED", "credit-card"),
        "comissoes_vendas": (
            "Comissoes de Vendas",
            "despesa",
            "#4F46E5",
            "badge-dollar-sign",
        ),
        "frete_vendas": ("Fretes sobre Vendas", "despesa", "#0891B2", "truck"),
        "repasse_entrega": ("Repasse Entregador", "despesa", "#0E7490", "route"),
        "compra_mercadorias": ("Compra de Mercadorias", "despesa", "#92400E", "boxes"),
        "folha_operacional": ("Folha RH Operacional", "despesa", "#BE123C", "users"),
        "aluguel_loja": ("Aluguel da Loja", "despesa", "#64748B", "store"),
        "energia": ("Energia Eletrica", "despesa", "#CA8A04", "zap"),
        "marketing": ("Marketing e Criativos", "despesa", "#DB2777", "megaphone"),
        "impostos": ("Impostos sobre Vendas", "despesa", "#991B1B", "landmark"),
    }

    result: dict[str, dict[str, Any]] = {}
    for key, dre_spec in dre_specs.items():
        sub_id = _ensure_dre_subcategory(
            db,
            tenant_id=tenant_id,
            category_name=dre_spec[0],
            category_nature=dre_spec[1],
            category_order=dre_spec[2],
            sub_name=dre_spec[3],
            tipo_custo=dre_spec[4],
            base_rateio=dre_spec[5],
            custo_pe=dre_spec[6],
        )
        cat_name, tipo, color, icon = category_specs[key]
        cat_id = _ensure_financial_category(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            name=cat_name,
            tipo=tipo,
            dre_subcategory_id=sub_id,
            tipo_custo=dre_spec[6],
            color=color,
            icon=icon,
        )
        result[key] = {"dre_subcategory_id": sub_id, "category_id": cat_id}
    return result
