"""Seed an operational demo tenant for sales, finance, stock, delivery and RH.

Default mode is dry-run. Use --apply to persist data.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import text


if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))


DEFAULT_TARGET_EMAIL = "corepeterp@gmail.com"
DEFAULT_SOURCE_EMAIL = "atacadaopetpp@gmail.com"
PRODUCTION_ENVS = {"prod", "production"}
CENT = Decimal("0.01")
DEFAULT_TAX_PERCENT = Decimal("6.25")
DEFAULT_COMMISSION_PERCENT = Decimal("4.00")
DEMO_PRICE_PROFILES = [
    (Decimal("151.00"), Decimal("239.90")),
    (Decimal("118.00"), Decimal("189.90")),
    (Decimal("104.00"), Decimal("169.90")),
    (Decimal("76.00"), Decimal("129.90")),
    (Decimal("54.00"), Decimal("94.90")),
    (Decimal("43.00"), Decimal("76.90")),
    (Decimal("30.00"), Decimal("59.90")),
    (Decimal("24.90"), Decimal("49.90")),
    (Decimal("17.00"), Decimal("34.90")),
    (Decimal("10.00"), Decimal("24.90")),
    (Decimal("137.00"), Decimal("219.90")),
    (Decimal("88.00"), Decimal("149.90")),
]


@dataclass(frozen=True)
class SaleScenario:
    number: str
    channel: str
    client_key: str
    payment_key: str
    items: tuple[tuple[int, Decimal], ...]
    days_ago: int
    due_in_days: int = 0
    discount_value: Decimal = Decimal("0")
    discount_percent: Decimal = Decimal("0")
    coupon: str | None = None
    delivery: bool = False
    delivery_fee: Decimal = Decimal("0")
    driver_share: Decimal = Decimal("0")
    delivery_km: Decimal = Decimal("0")
    route_number: str | None = None
    route_status: str | None = None
    received_ratio: Decimal = Decimal("1")
    installments: int = 1
    card_brand: str | None = None
    order_id: str | None = None
    order_origin: str | None = None
    order_status: str | None = None
    commissioned: bool = False
    observations: str = ""


@dataclass(frozen=True)
class FixedPayable:
    document: str
    description: str
    category_key: str
    amount: Decimal
    days_ago: int
    due_in_days: int
    paid: bool
    supplier_key: str
    channel: str | None = None


def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def decimal_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def build_demo_scenarios() -> list[SaleScenario]:
    """Return the sales path Lucas wants visible in the demo."""

    return [
        SaleScenario(
            number="DEMO-VEN-001",
            channel="loja_fisica",
            client_key="ana",
            payment_key="pix",
            items=((0, Decimal("1")), (1, Decimal("2"))),
            days_ago=1,
            observations="Venda balcão sem desconto, baixa imediata no PIX.",
            commissioned=True,
        ),
        SaleScenario(
            number="DEMO-VEN-002",
            channel="loja_fisica",
            client_key="joao",
            payment_key="debito",
            items=((2, Decimal("1")), (3, Decimal("1"))),
            days_ago=3,
            due_in_days=1,
            discount_value=Decimal("12.00"),
            delivery=True,
            delivery_fee=Decimal("18.00"),
            driver_share=Decimal("12.00"),
            delivery_km=Decimal("6.4"),
            route_number="DEMO-ROT-001",
            route_status="concluida",
            card_brand="visa",
            observations="Venda balcão com entrega, desconto e débito recebido.",
            commissioned=True,
        ),
        SaleScenario(
            number="DEMO-VEN-003",
            channel="app_mobile",
            client_key="maria",
            payment_key="credito",
            items=((0, Decimal("1")), (4, Decimal("2"))),
            days_ago=5,
            due_in_days=12,
            discount_percent=Decimal("10.00"),
            coupon="APP10",
            delivery=True,
            delivery_fee=Decimal("14.00"),
            driver_share=Decimal("9.00"),
            delivery_km=Decimal("4.2"),
            route_number="DEMO-ROT-002",
            route_status="em_rota",
            received_ratio=Decimal("0.40"),
            installments=3,
            card_brand="master",
            order_id="DEMO-APP-001",
            order_origin="app",
            order_status="em_preparo",
            observations="Venda pelo app com campanha, cartão parcelado e baixa parcial.",
            commissioned=True,
        ),
        SaleScenario(
            number="DEMO-VEN-004",
            channel="ecommerce",
            client_key="ana",
            payment_key="credito",
            items=((1, Decimal("1")), (5, Decimal("1"))),
            days_ago=2,
            due_in_days=18,
            delivery=True,
            delivery_fee=Decimal("22.00"),
            driver_share=Decimal("14.00"),
            delivery_km=Decimal("9.1"),
            route_number="DEMO-ROT-003",
            route_status="pendente",
            received_ratio=Decimal("0"),
            installments=2,
            card_brand="elo",
            order_id="DEMO-ECO-001",
            order_origin="web",
            order_status="aguardando_pagamento",
            observations="Pedido e-commerce com previsão de recebimento futura.",
        ),
        SaleScenario(
            number="DEMO-VEN-005",
            channel="loja_fisica",
            client_key="distribuidora",
            payment_key="dinheiro",
            items=((3, Decimal("3")),),
            days_ago=8,
            discount_value=Decimal("5.00"),
            observations="Venda no dinheiro com desconto manual e baixa total.",
        ),
        SaleScenario(
            number="DEMO-VEN-006",
            channel="app_mobile",
            client_key="joao",
            payment_key="pix",
            items=((2, Decimal("2")), (0, Decimal("1"))),
            days_ago=10,
            coupon="FIDELIDADE5",
            discount_value=Decimal("8.00"),
            order_id="DEMO-APP-002",
            order_origin="app",
            order_status="entregue",
            observations="Venda pelo app com campanha de fidelidade e retirada.",
            commissioned=True,
        ),
    ]


def build_fixed_payables() -> list[FixedPayable]:
    return [
        FixedPayable(
            document="DEMO-CP-COMPRA-001",
            description="Demo operacional - Compra de mercadorias para reposicao",
            category_key="compra_mercadorias",
            amount=Decimal("1450.00"),
            days_ago=12,
            due_in_days=0,
            paid=True,
            supplier_key="fornecedor",
        ),
        FixedPayable(
            document="DEMO-CP-FOLHA-001",
            description="Demo operacional - Folha RH equipe de loja",
            category_key="folha_operacional",
            amount=Decimal("3650.00"),
            days_ago=6,
            due_in_days=0,
            paid=True,
            supplier_key="funcionario_vendedor",
            channel="loja_fisica",
        ),
        FixedPayable(
            document="DEMO-CP-ALUGUEL-001",
            description="Demo operacional - Aluguel da loja",
            category_key="aluguel_loja",
            amount=Decimal("1850.00"),
            days_ago=7,
            due_in_days=0,
            paid=True,
            supplier_key="fornecedor",
        ),
        FixedPayable(
            document="DEMO-CP-ENERGIA-001",
            description="Demo operacional - Energia eletrica prevista",
            category_key="energia",
            amount=Decimal("420.00"),
            days_ago=1,
            due_in_days=2,
            paid=False,
            supplier_key="fornecedor",
        ),
        FixedPayable(
            document="DEMO-CP-IMPOSTO-001",
            description="Demo operacional - Simples Nacional previsto",
            category_key="impostos",
            amount=Decimal("680.00"),
            days_ago=1,
            due_in_days=8,
            paid=False,
            supplier_key="fornecedor",
        ),
        FixedPayable(
            document="DEMO-CP-COMISSAO-BASE",
            description="Demo operacional - Comissao de vendas prevista",
            category_key="comissoes_vendas",
            amount=Decimal("180.00"),
            days_ago=1,
            due_in_days=7,
            paid=False,
            supplier_key="funcionario_vendedor",
            channel="loja_fisica",
        ),
        FixedPayable(
            document="DEMO-CP-MKT-001",
            description="Demo operacional - Campanhas e criativos",
            category_key="marketing",
            amount=Decimal("300.00"),
            days_ago=4,
            due_in_days=0,
            paid=True,
            supplier_key="fornecedor",
            channel="ecommerce",
        ),
    ]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cria uma base demo operacional com vendas, financeiro, estoque, entrega e RH."
    )
    parser.add_argument("--target-email", default=DEFAULT_TARGET_EMAIL)
    parser.add_argument("--source-email", default=DEFAULT_SOURCE_EMAIL)
    parser.add_argument("--base-date", default=date.today().isoformat())
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--skip-catalog-import", action="store_true")
    parser.add_argument("--allow-production-apply", action="store_true")
    return parser


def _environment_name() -> str:
    for name in ("APP_ENV", "ENVIRONMENT", "ENV"):
        value = os.getenv(name)
        if value:
            return value.strip().lower()
    return ""


def assert_safe_environment(
    *, apply: bool, environment: str, allow_production_apply: bool
) -> None:
    if apply and environment in PRODUCTION_ENVS and not allow_production_apply:
        raise ValueError(
            "Ambiente production/prod detectado; --apply bloqueado sem "
            "--allow-production-apply."
        )


def _fail(message: str, dry_run: bool) -> int:
    print(
        json.dumps(
            {"ok": False, "error": message, "dry_run": dry_run},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 1


def _set_tenant_context(db, tenant_id: str) -> None:
    db.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": tenant_id},
    )


def _resolve_tenant_context(db, target_email: str) -> dict[str, Any]:
    row = (
        db.execute(
            text(
                """
                SELECT id AS user_id,
                       email,
                       COALESCE(NULLIF(nome, ''), email) AS user_name,
                       tenant_id::text AS tenant_id
                FROM users
                WHERE lower(email) = lower(:email)
                ORDER BY id
                LIMIT 1
                """
            ),
            {"email": target_email.strip()},
        )
        .mappings()
        .first()
    )
    if not row:
        raise ValueError(f"Usuario alvo nao encontrado: {target_email}")
    if not row["tenant_id"]:
        raise ValueError(f"Usuario alvo sem tenant: {target_email}")
    return dict(row)


def _resolve_source_tenant_id(db, source_email: str) -> str | None:
    row = db.execute(
        text(
            """
            SELECT tenant_id::text
            FROM users
            WHERE lower(email) = lower(:email)
              AND tenant_id IS NOT NULL
            ORDER BY id
            LIMIT 1
            """
        ),
        {"email": source_email.strip()},
    ).first()
    return str(row[0]) if row else None


def _maybe_import_catalog(
    *,
    db,
    source_email: str,
    target_tenant_id: str,
    user_id: int,
    dry_run: bool,
    skip: bool,
) -> dict[str, Any]:
    if skip:
        return {"status": "skipped"}

    source_tenant_id = _resolve_source_tenant_id(db, source_email)
    if not source_tenant_id:
        return {
            "status": "source_missing",
            "source_email": source_email,
            "message": "Tenant fonte nao existe neste banco.",
        }
    if source_tenant_id == target_tenant_id:
        return {"status": "skipped_same_tenant", "source_email": source_email}

    from app.services.base_catalog_import_service import import_base_catalog

    result = import_base_catalog(
        db=db,
        source_tenant_id=source_tenant_id,
        target_tenant_id=target_tenant_id,
        user_id=user_id,
        dry_run=dry_run,
    )
    result["status"] = "dry_run" if dry_run else "applied"
    return result


def _scalar(db, sql: str, params: dict[str, Any]) -> Any:
    return db.execute(text(sql), params).scalar()


def _one_mapping(db, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    row = db.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def _all_mappings(db, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(sql), params).mappings().all()]


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


def _ensure_accounting_setup(db, *, tenant_id: str, user_id: int) -> dict[str, dict[str, Any]]:
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
        "receita_produtos": ("Receitas de Vendas", "receita", "#059669", "shopping-cart"),
        "receita_app": ("Vendas App", "receita", "#0F766E", "smartphone"),
        "receita_ecommerce": ("Vendas Ecommerce", "receita", "#2563EB", "globe"),
        "descontos": ("Descontos Concedidos", "despesa", "#EA580C", "badge-percent"),
        "cmv": ("CMV", "despesa", "#475569", "package"),
        "taxas_cartao": ("Taxas de Cartao", "despesa", "#7C3AED", "credit-card"),
        "comissoes_vendas": ("Comissoes de Vendas", "despesa", "#4F46E5", "badge-dollar-sign"),
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


def _ensure_bank_account(
    db,
    *,
    tenant_id: str,
    user_id: int,
    name: str,
    tipo: str,
    saldo: Decimal,
    color: str,
    icon: str,
) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM contas_bancarias
        WHERE tenant_id = :tenant_id AND lower(nome) = lower(:name)
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "name": name},
    )
    if existing:
        db.execute(
            text(
                """
                UPDATE contas_bancarias
                SET tipo = :tipo,
                    saldo_inicial = :saldo,
                    saldo_atual = :saldo,
                    cor = :color,
                    icone = :icon,
                    ativa = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "id": existing,
                "tipo": tipo,
                "saldo": saldo,
                "color": color,
                "icon": icon,
            },
        )
        return int(existing)

    return int(
        _scalar(
            db,
            """
            INSERT INTO contas_bancarias (
                nome, tipo, saldo_inicial, saldo_atual, cor, icone,
                instituicao_bancaria, ativa, observacoes, user_id, tenant_id,
                created_at, updated_at
            )
            VALUES (
                :name, :tipo, :saldo, :saldo, :color, :icon,
                :institution, true, :obs, :user_id, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "name": name,
                "tipo": tipo,
                "saldo": saldo,
                "color": color,
                "icon": icon,
                "institution": tipo == "corrente",
                "obs": "Conta demo operacional",
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )


def _ensure_payment_method(
    db,
    *,
    tenant_id: str,
    user_id: int,
    name: str,
    tipo: str,
    taxa_percentual: Decimal,
    taxa_fixa: Decimal,
    prazo_dias: int,
    bank_id: int,
    operadora: str | None = None,
    tipo_cartao: str | None = None,
    bandeira: str | None = None,
    requer_nsu: bool = False,
    permite_parcelamento: bool = False,
    max_parcelas: int = 1,
) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM formas_pagamento
        WHERE tenant_id = :tenant_id AND lower(nome) = lower(:name)
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "name": name},
    )
    payload = {
        "name": name,
        "tipo": tipo,
        "taxa_percentual": taxa_percentual,
        "taxa_fixa": taxa_fixa,
        "prazo_dias": prazo_dias,
        "bank_id": bank_id,
        "operadora": operadora,
        "tipo_cartao": tipo_cartao,
        "bandeira": bandeira,
        "requer_nsu": requer_nsu,
        "permite_parcelamento": permite_parcelamento,
        "max_parcelas": max_parcelas,
        "user_id": user_id,
        "tenant_id": tenant_id,
    }
    if existing:
        db.execute(
            text(
                """
                UPDATE formas_pagamento
                SET tipo = :tipo,
                    taxa_percentual = :taxa_percentual,
                    taxa_fixa = :taxa_fixa,
                    prazo_dias = :prazo_dias,
                    prazo_recebimento = :prazo_dias,
                    operadora = :operadora,
                    gera_contas_receber = true,
                    split_parcelas = :permite_parcelamento,
                    conta_bancaria_destino_id = :bank_id,
                    requer_nsu = :requer_nsu,
                    tipo_cartao = :tipo_cartao,
                    bandeira = :bandeira,
                    ativo = true,
                    permite_parcelamento = :permite_parcelamento,
                    max_parcelas = :max_parcelas,
                    parcelas_maximas = :max_parcelas,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**payload, "id": existing},
        )
        payment_id = int(existing)
    else:
        payment_id = int(
            _scalar(
                db,
                """
                INSERT INTO formas_pagamento (
                    nome, tipo, taxa_percentual, taxa_fixa, prazo_dias,
                    prazo_recebimento, operadora, gera_contas_receber, split_parcelas,
                    conta_bancaria_destino_id, requer_nsu, tipo_cartao, bandeira,
                    ativo, permite_parcelamento, max_parcelas, parcelas_maximas,
                    user_id, tenant_id, created_at, updated_at
                )
                VALUES (
                    :name, :tipo, :taxa_percentual, :taxa_fixa, :prazo_dias,
                    :prazo_dias, :operadora, true, :permite_parcelamento,
                    :bank_id, :requer_nsu, :tipo_cartao, :bandeira,
                    true, :permite_parcelamento, :max_parcelas, :max_parcelas,
                    :user_id, :tenant_id, now(), now()
                )
                RETURNING id
                """,
                payload,
            )
        )

    db.execute(
        text(
            """
            DELETE FROM formas_pagamento_taxas
            WHERE tenant_id = :tenant_id AND forma_pagamento_id = :payment_id
            """
        ),
        {"tenant_id": tenant_id, "payment_id": payment_id},
    )
    if permite_parcelamento:
        for parcelas in range(1, max_parcelas + 1):
            taxa = taxa_percentual + Decimal("0.35") * Decimal(parcelas - 1)
            db.execute(
                text(
                    """
                    INSERT INTO formas_pagamento_taxas (
                        forma_pagamento_id, parcelas, taxa_percentual, descricao,
                        created_at, updated_at, tenant_id
                    )
                    VALUES (
                        :payment_id, :parcelas, :taxa, :descricao,
                        now(), now(), :tenant_id
                    )
                    """
                ),
                {
                    "payment_id": payment_id,
                    "parcelas": parcelas,
                    "taxa": money(taxa),
                    "descricao": f"{parcelas}x demo",
                    "tenant_id": tenant_id,
                },
            )

    return payment_id


def _ensure_tax_configuration(
    db,
    *,
    tenant_id: str,
    user_id: int,
    tax_percent: Decimal = DEFAULT_TAX_PERCENT,
) -> None:
    fiscal_exists = _scalar(
        db,
        """
        SELECT id FROM empresa_config_fiscal
        WHERE tenant_id = :tenant_id
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    fiscal_payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "tax_percent": tax_percent,
    }
    if fiscal_exists:
        db.execute(
            text(
                """
                UPDATE empresa_config_fiscal
                SET uf = 'SP',
                    regime_tributario = 'simples_nacional',
                    contribuinte_icms = true,
                    icms_aliquota_interna = 18.00,
                    icms_aliquota_interestadual = 12.00,
                    aplica_difal = false,
                    cfop_venda_interna = '5102',
                    cfop_venda_interestadual = '6102',
                    cfop_compra = '1102',
                    pis_cst_padrao = '49',
                    pis_aliquota = 0.65,
                    cofins_cst_padrao = '49',
                    cofins_aliquota = 3.00,
                    municipio_iss = 'Sao Paulo',
                    iss_aliquota = 2.00,
                    simples_ativo = true,
                    simples_anexo = 'I',
                    aliquota_simples_vigente = :tax_percent,
                    aliquota_simples_sugerida = :tax_percent,
                    folha_valor_base_mensal = 4300.00,
                    inss_patronal_percentual = 20.00,
                    fgts_percentual = 8.00,
                    cnae_principal = '4789-0/04',
                    cnae_descricao = 'Comercio varejista de animais vivos e artigos para animais',
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**fiscal_payload, "id": fiscal_exists},
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO empresa_config_fiscal (
                    tenant_id, uf, regime_tributario, contribuinte_icms,
                    icms_aliquota_interna, icms_aliquota_interestadual,
                    aplica_difal, cfop_venda_interna, cfop_venda_interestadual,
                    cfop_compra, pis_cst_padrao, pis_aliquota,
                    cofins_cst_padrao, cofins_aliquota, municipio_iss,
                    iss_aliquota, iss_retido, herdado_do_estado, simples_ativo,
                    simples_anexo, aliquota_simples_vigente,
                    aliquota_simples_sugerida, folha_valor_base_mensal,
                    inss_patronal_percentual, fgts_percentual, cnae_principal,
                    cnae_descricao, created_at, updated_at
                )
                VALUES (
                    :tenant_id, 'SP', 'simples_nacional', true,
                    18.00, 12.00,
                    false, '5102', '6102',
                    '1102', '49', 0.65,
                    '49', 3.00, 'Sao Paulo',
                    2.00, false, false, true,
                    'I', :tax_percent,
                    :tax_percent, 4300.00,
                    20.00, 8.00, '4789-0/04',
                    'Comercio varejista de animais vivos e artigos para animais',
                    now(), now()
                )
                """
            ),
            fiscal_payload,
        )

    tax_exists = _scalar(
        db,
        """
        SELECT id FROM configuracao_tributaria
        WHERE tenant_id = :tenant_id
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    if tax_exists:
        db.execute(
            text(
                """
                UPDATE configuracao_tributaria
                SET usuario_id = :user_id,
                    regime = 'simples_nacional',
                    anexo_simples = 'I',
                    faixa_simples = 'Faixa 2 demo',
                    aliquota_efetiva_simples = :tax_percent,
                    estado = 'SP',
                    aliquota_icms = 18.00,
                    incluir_icms_dre = true,
                    aliquota_iss = 2.00,
                    incluir_iss_dre = true,
                    atualizado_em = now(),
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**fiscal_payload, "id": tax_exists},
        )
        return

    db.execute(
        text(
            """
            INSERT INTO configuracao_tributaria (
                usuario_id, regime, anexo_simples, faixa_simples,
                aliquota_efetiva_simples, estado, aliquota_icms,
                incluir_icms_dre, aliquota_iss, incluir_iss_dre,
                criado_em, atualizado_em, tenant_id, created_at, updated_at
            )
            VALUES (
                :user_id, 'simples_nacional', 'I', 'Faixa 2 demo',
                :tax_percent, 'SP', 18.00,
                true, 2.00, true,
                now(), now(), :tenant_id, now(), now()
            )
            """
        ),
        fiscal_payload,
    )


def _ensure_commission_configuration(
    db,
    *,
    tenant_id: str,
    funcionario_id: int,
    percent: Decimal = DEFAULT_COMMISSION_PERCENT,
) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM comissoes_configuracao
        WHERE tenant_id = :tenant_id
          AND funcionario_id = :funcionario_id
          AND tipo = 'geral'
          AND referencia_id = 0
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "funcionario_id": funcionario_id},
    )
    payload = {
        "tenant_id": tenant_id,
        "funcionario_id": funcionario_id,
        "percent": percent,
    }
    if existing:
        db.execute(
            text(
                """
                UPDATE comissoes_configuracao
                SET percentual = :percent,
                    ativo = true,
                    tipo_calculo = 'percentual_venda_liquida',
                    desconta_taxa_cartao = true,
                    desconta_impostos = true,
                    desconta_custo_entrega = true,
                    comissao_venda_parcial = true,
                    percentual_loja = 100,
                    permite_edicao_venda = true,
                    observacoes = 'Demo operacional - regra geral de comissao',
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**payload, "id": existing},
        )
        return int(existing)

    return int(
        _scalar(
            db,
            """
            INSERT INTO comissoes_configuracao (
                funcionario_id, tipo, referencia_id, percentual, ativo,
                tipo_calculo, desconta_taxa_cartao, desconta_impostos,
                desconta_custo_entrega, comissao_venda_parcial,
                percentual_loja, permite_edicao_venda, observacoes,
                created_at, updated_at, tenant_id
            )
            VALUES (
                :funcionario_id, 'geral', 0, :percent, true,
                'percentual_venda_liquida', true, true,
                true, true,
                100, true, 'Demo operacional - regra geral de comissao',
                now(), now(), :tenant_id
            )
            RETURNING id
            """,
            payload,
        )
    )


def _ensure_support_data(
    db, *, tenant_id: str, user_id: int, base_date: date
) -> dict[str, Any]:
    categories = _ensure_accounting_setup(db, tenant_id=tenant_id, user_id=user_id)

    bank_main_id = _ensure_bank_account(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        name="Conta Banco Demo",
        tipo="corrente",
        saldo=Decimal("2500.00"),
        color="#0F766E",
        icon="landmark",
    )
    bank_cash_id = _ensure_bank_account(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        name="Caixa Loja Demo",
        tipo="caixa_fisico",
        saldo=Decimal("600.00"),
        color="#EA580C",
        icon="wallet",
    )

    payment_methods = {
        "dinheiro": _ensure_payment_method(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            name="Dinheiro",
            tipo="dinheiro",
            taxa_percentual=Decimal("0"),
            taxa_fixa=Decimal("0"),
            prazo_dias=0,
            bank_id=bank_cash_id,
        ),
        "pix": _ensure_payment_method(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            name="PIX",
            tipo="pix",
            taxa_percentual=Decimal("0"),
            taxa_fixa=Decimal("0"),
            prazo_dias=0,
            bank_id=bank_main_id,
        ),
        "debito": _ensure_payment_method(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            name="Cartao de debito",
            tipo="cartao_debito",
            taxa_percentual=Decimal("1.89"),
            taxa_fixa=Decimal("0"),
            prazo_dias=1,
            bank_id=bank_main_id,
            operadora="Stone",
            tipo_cartao="debito",
            bandeira="visa",
            requer_nsu=True,
        ),
        "credito": _ensure_payment_method(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            name="Cartao de credito",
            tipo="cartao_credito",
            taxa_percentual=Decimal("3.49"),
            taxa_fixa=Decimal("0"),
            prazo_dias=30,
            bank_id=bank_main_id,
            operadora="Stone",
            tipo_cartao="credito",
            bandeira="master",
            requer_nsu=True,
            permite_parcelamento=True,
            max_parcelas=6,
        ),
    }

    cargo_vendedor_id = _ensure_cargo(
        db,
        tenant_id=tenant_id,
        name="Vendedor Demo",
        salary=Decimal("2500.00"),
        inss=Decimal("20.00"),
        fgts=Decimal("8.00"),
    )
    cargo_entregador_id = _ensure_cargo(
        db,
        tenant_id=tenant_id,
        name="Entregador Demo",
        salary=Decimal("1800.00"),
        inss=Decimal("20.00"),
        fgts=Decimal("8.00"),
    )

    clients = {
        "ana": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-CLI-001",
            name="Ana Costa",
            kind="cliente",
            email="ana.demo@sistemapet.local",
            phone="(11) 90000-1001",
            address="Rua das Palmeiras",
            number="120",
            district="Centro",
            city="Sao Paulo",
            state="SP",
        ),
        "joao": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-CLI-002",
            name="Joao Santos",
            kind="cliente",
            email="joao.demo@sistemapet.local",
            phone="(11) 90000-1002",
            address="Av. Pet Shop",
            number="455",
            district="Mooca",
            city="Sao Paulo",
            state="SP",
        ),
        "maria": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-CLI-003",
            name="Maria Oliveira",
            kind="cliente",
            email="maria.demo@sistemapet.local",
            phone="(11) 90000-1003",
            address="Rua dos Lirios",
            number="87",
            district="Tatuape",
            city="Sao Paulo",
            state="SP",
        ),
        "distribuidora": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-FOR-001",
            name="Distribuidora Pet Brasil",
            kind="fornecedor",
            email="compras.demo@sistemapet.local",
            phone="(11) 3333-0101",
            address="Rodovia dos Petiscos",
            number="1000",
            district="Industrial",
            city="Guarulhos",
            state="SP",
        ),
        "fornecedor": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-FOR-002",
            name="Fornecedor Demo Financeiro",
            kind="fornecedor",
            email="financeiro.fornecedor.demo@sistemapet.local",
            phone="(11) 3333-0202",
            address="Rua Financeira",
            number="42",
            district="Centro",
            city="Sao Paulo",
            state="SP",
        ),
        "funcionario_vendedor": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-FUNC-001",
            name="Beatriz Vendedora Demo",
            kind="funcionario",
            email="beatriz.vendas.demo@sistemapet.local",
            phone="(11) 95555-0101",
            address="Rua Equipe CorePet",
            number="10",
            district="Centro",
            city="Sao Paulo",
            state="SP",
            cargo_id=cargo_vendedor_id,
            salary=Decimal("2500.00"),
            controla_rh=True,
            commission_partner=True,
        ),
        "entregador": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-ENT-001",
            name="Carlos Entregador Demo",
            kind="funcionario",
            email="carlos.entrega.demo@sistemapet.local",
            phone="(11) 95555-0202",
            address="Rua das Rotas",
            number="77",
            district="Ipiranga",
            city="Sao Paulo",
            state="SP",
            cargo_id=cargo_entregador_id,
            salary=Decimal("1800.00"),
            controla_rh=True,
            is_entregador=True,
            valor_por_km=Decimal("2.20"),
        ),
    }

    _ensure_delivery_config(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        entregador_id=clients["entregador"],
    )
    _ensure_tax_configuration(db, tenant_id=tenant_id, user_id=user_id)
    commission_config_id = _ensure_commission_configuration(
        db,
        tenant_id=tenant_id,
        funcionario_id=clients["funcionario_vendedor"],
    )

    return {
        "categories": categories,
        "banks": {"main": bank_main_id, "cash": bank_cash_id},
        "payments": payment_methods,
        "people": clients,
        "commission_config_id": commission_config_id,
        "base_date": base_date,
    }


def _ensure_cargo(
    db,
    *,
    tenant_id: str,
    name: str,
    salary: Decimal,
    inss: Decimal,
    fgts: Decimal,
) -> int:
    existing = _scalar(
        db,
        "SELECT id FROM cargos WHERE tenant_id = :tenant_id AND lower(nome) = lower(:name) LIMIT 1",
        {"tenant_id": tenant_id, "name": name},
    )
    if existing:
        db.execute(
            text(
                """
                UPDATE cargos
                SET salario_base = :salary,
                    inss_patronal_percentual = :inss,
                    fgts_percentual = :fgts,
                    gera_ferias = true,
                    gera_decimo_terceiro = true,
                    ativo = true,
                    regime_remuneracao = 'clt',
                    gera_encargos = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": existing, "salary": salary, "inss": inss, "fgts": fgts},
        )
        return int(existing)

    return int(
        _scalar(
            db,
            """
            INSERT INTO cargos (
                nome, descricao, salario_base, inss_patronal_percentual,
                fgts_percentual, gera_ferias, gera_decimo_terceiro, ativo,
                regime_remuneracao, gera_encargos, tenant_id, created_at, updated_at
            )
            VALUES (
                :name, 'Cargo demo operacional', :salary, :inss,
                :fgts, true, true, true, 'clt', true, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "name": name,
                "salary": salary,
                "inss": inss,
                "fgts": fgts,
                "tenant_id": tenant_id,
            },
        )
    )


def _ensure_person(
    db,
    *,
    tenant_id: str,
    user_id: int,
    code: str,
    name: str,
    kind: str,
    email: str,
    phone: str,
    address: str,
    number: str,
    district: str,
    city: str,
    state: str,
    cargo_id: int | None = None,
    salary: Decimal | None = None,
    controla_rh: bool = False,
    is_entregador: bool = False,
    valor_por_km: Decimal | None = None,
    commission_partner: bool = False,
) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM clientes
        WHERE tenant_id = :tenant_id AND codigo = :code
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "code": code},
    )
    tipo_pessoa = "J" if kind == "fornecedor" else "F"
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "code": code,
        "kind": kind,
        "tipo_pessoa": tipo_pessoa,
        "name": name,
        "email": email,
        "phone": phone,
        "address": address,
        "number": number,
        "district": district,
        "city": city,
        "state": state,
        "cargo_id": cargo_id,
        "salary": salary,
        "controla_rh": controla_rh,
        "is_entregador": is_entregador,
        "valor_por_km": valor_por_km,
        "commission_partner": commission_partner,
    }
    if existing:
        db.execute(
            text(
                """
                UPDATE clientes
                SET tipo_cadastro = :kind,
                    tipo_pessoa = :tipo_pessoa,
                    nome = :name,
                    email = :email,
                    telefone = :phone,
                    celular = :phone,
                    endereco = :address,
                    endereco_entrega = :address || ', ' || :number || ' - ' || :district,
                    numero = :number,
                    bairro = :district,
                    cidade = :city,
                    estado = :state,
                    cargo_id = :cargo_id,
                    salario_base_override = :salary,
                    liquido_combinado = :salary,
                    controla_rh = :controla_rh,
                    is_entregador = :is_entregador,
                    recebe_repasse = :is_entregador,
                    gera_conta_pagar = :is_entregador,
                    recebe_comissao_entrega = :is_entregador,
                    parceiro_ativo = :commission_partner,
                    parceiro_desde = CASE
                        WHEN :commission_partner THEN COALESCE(parceiro_desde, now())
                        ELSE parceiro_desde
                    END,
                    parceiro_observacoes = CASE
                        WHEN :commission_partner THEN 'Demo operacional - parceiro comissionado'
                        ELSE parceiro_observacoes
                    END,
                    data_fechamento_comissao = CASE
                        WHEN :commission_partner THEN 5
                        ELSE data_fechamento_comissao
                    END,
                    parceiro_tipo_acerto = CASE
                        WHEN :commission_partner THEN 'mensal'
                        ELSE parceiro_tipo_acerto
                    END,
                    parceiro_dia_acerto = CASE
                        WHEN :commission_partner THEN 5
                        ELSE parceiro_dia_acerto
                    END,
                    parceiro_notificar = CASE
                        WHEN :commission_partner THEN true
                        ELSE parceiro_notificar
                    END,
                    parceiro_email_principal = CASE
                        WHEN :commission_partner THEN :email
                        ELSE parceiro_email_principal
                    END,
                    entregador_ativo = :is_entregador,
                    entregador_padrao = :is_entregador,
                    gera_conta_pagar_custo_entrega = :is_entregador,
                    tipo_vinculo_entrega = CASE WHEN :is_entregador THEN 'interno' ELSE tipo_vinculo_entrega END,
                    valor_por_km = :valor_por_km,
                    valor_por_km_entrega = :valor_por_km,
                    moto_propria = :is_entregador,
                    modelo_custo_entrega = CASE WHEN :is_entregador THEN 'km' ELSE modelo_custo_entrega END,
                    tipo_acerto_entrega = CASE WHEN :is_entregador THEN 'semanal' ELSE tipo_acerto_entrega END,
                    ativo = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**payload, "id": existing},
        )
        return int(existing)

    return int(
        _scalar(
            db,
            """
            INSERT INTO clientes (
                user_id, codigo, tipo_cadastro, tipo_pessoa, nome, email,
                telefone, celular, endereco, endereco_entrega, numero, bairro,
                cidade, estado, cargo_id, salario_base_override, liquido_combinado,
                controla_rh, is_entregador, is_terceirizado, recebe_repasse,
                gera_conta_pagar, recebe_comissao_entrega, parceiro_ativo,
                parceiro_desde, parceiro_observacoes, data_fechamento_comissao,
                parceiro_tipo_acerto, parceiro_dia_acerto, parceiro_notificar,
                parceiro_email_principal, entregador_ativo,
                entregador_padrao, gera_conta_pagar_custo_entrega,
                tipo_vinculo_entrega, valor_por_km, valor_por_km_entrega,
                modelo_custo_entrega, tipo_acerto_entrega, controla_dre,
                moto_propria, ativo, credito, tenant_id, created_at, updated_at
            )
            VALUES (
                :user_id, :code, :kind, :tipo_pessoa, :name, :email,
                :phone, :phone, :address,
                :address || ', ' || :number || ' - ' || :district,
                :number, :district, :city, :state, :cargo_id, :salary, :salary,
                :controla_rh, :is_entregador, false, :is_entregador,
                :is_entregador, :is_entregador, :commission_partner,
                CASE WHEN :commission_partner THEN now() ELSE NULL END,
                CASE
                    WHEN :commission_partner THEN 'Demo operacional - parceiro comissionado'
                    ELSE NULL
                END,
                CASE WHEN :commission_partner THEN 5 ELSE NULL END,
                CASE WHEN :commission_partner THEN 'mensal' ELSE 'mensal' END,
                CASE WHEN :commission_partner THEN 5 ELSE 1 END,
                true,
                CASE WHEN :commission_partner THEN :email ELSE NULL END,
                :is_entregador, :is_entregador, :is_entregador,
                CASE WHEN :is_entregador THEN 'interno' ELSE NULL END,
                :valor_por_km, :valor_por_km,
                CASE WHEN :is_entregador THEN 'km' ELSE NULL END,
                CASE WHEN :is_entregador THEN 'semanal' ELSE NULL END,
                true, :is_entregador, true, 0, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            payload,
        )
    )


def _ensure_delivery_config(
    db, *, tenant_id: str, user_id: int, entregador_id: int
) -> None:
    existing = _scalar(
        db,
        """
        SELECT id FROM configuracoes_entrega
        WHERE tenant_id = :tenant_id AND user_id = :user_id
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "user_id": user_id},
    )
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "entregador_id": entregador_id,
        "logradouro": "Av. CorePet Demo",
        "cep": "01001-000",
        "numero": "100",
        "complemento": "Loja demo",
        "bairro": "Centro",
        "cidade": "Sao Paulo",
        "estado": "SP",
    }
    if existing:
        db.execute(
            text(
                """
                UPDATE configuracoes_entrega
                SET entregador_padrao_id = :entregador_id,
                    logradouro = :logradouro,
                    cep = :cep,
                    numero = :numero,
                    complemento = :complemento,
                    bairro = :bairro,
                    cidade = :cidade,
                    estado = :estado,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**payload, "id": existing},
        )
        return

    db.execute(
        text(
            """
            INSERT INTO configuracoes_entrega (
                user_id, entregador_padrao_id, logradouro, cep, numero,
                complemento, bairro, cidade, estado, tenant_id, created_at, updated_at
            )
            VALUES (
                :user_id, :entregador_id, :logradouro, :cep, :numero,
                :complemento, :bairro, :cidade, :estado, :tenant_id, now(), now()
            )
            """
        ),
        payload,
    )


def _cleanup_previous_demo(db, *, tenant_id: str) -> None:
    params = {"tenant_id": tenant_id}
    statements = [
        "DELETE FROM comissoes_vendas WHERE tenant_id = :tenant_id AND venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')",
        "DELETE FROM comissoes_itens WHERE tenant_id = :tenant_id AND venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')",
        "DELETE FROM movimentacoes_bancarias WHERE tenant_id = :tenant_id AND (fitid LIKE 'DEMO-%' OR memo LIKE 'Demo operacional%')",
        "DELETE FROM movimentacoes_financeiras WHERE tenant_id = :tenant_id AND (documento LIKE 'DEMO-%' OR descricao LIKE 'Demo operacional%')",
        "DELETE FROM fluxo_caixa WHERE tenant_id = :tenant_id AND (descricao LIKE 'Demo operacional%' OR origem_tipo = 'demo_operacional')",
        "DELETE FROM pagamentos WHERE tenant_id = :tenant_id AND conta_pagar_id IN (SELECT id FROM contas_pagar WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%')",
        "DELETE FROM recebimentos WHERE tenant_id = :tenant_id AND conta_receber_id IN (SELECT id FROM contas_receber WHERE tenant_id = :tenant_id AND (documento LIKE 'DEMO-%' OR venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')))",
        "DELETE FROM rotas_entrega_paradas WHERE tenant_id = :tenant_id AND (rota_id IN (SELECT id FROM rotas_entrega WHERE tenant_id = :tenant_id AND numero LIKE 'DEMO-ROT-%') OR venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'))",
        "DELETE FROM rotas_entrega WHERE tenant_id = :tenant_id AND (numero LIKE 'DEMO-ROT-%' OR venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'))",
        "DELETE FROM pedido_itens WHERE tenant_id = :tenant_id AND pedido_id LIKE 'DEMO-%'",
        "DELETE FROM pedidos WHERE tenant_id = :tenant_id AND pedido_id LIKE 'DEMO-%'",
        "DELETE FROM contas_pagar WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%'",
        "DELETE FROM contas_receber WHERE tenant_id = :tenant_id AND (documento LIKE 'DEMO-%' OR venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'))",
        "DELETE FROM venda_baixas WHERE tenant_id = :tenant_id AND venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')",
        "DELETE FROM venda_pagamentos WHERE tenant_id = :tenant_id AND venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')",
        "DELETE FROM venda_itens WHERE tenant_id = :tenant_id AND venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%')",
        "DELETE FROM movimentacoes_caixa WHERE tenant_id = :tenant_id AND (documento LIKE 'DEMO-%' OR venda_id IN (SELECT id FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'))",
        "DELETE FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'",
        "DELETE FROM estoque_movimentacoes WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%'",
        "DELETE FROM caixas WHERE tenant_id = :tenant_id AND observacoes_abertura LIKE 'Demo operacional%'",
    ]
    for sql in statements:
        db.execute(text(sql), params)


def _ensure_demo_product_category(db, *, tenant_id: str, user_id: int) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM categorias
        WHERE tenant_id = :tenant_id AND lower(nome) = lower('Racoes Demo')
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    if existing:
        return int(existing)
    return int(
        _scalar(
            db,
            """
            INSERT INTO categorias (
                nome, descricao, cor, icone, ativo, user_id, tenant_id,
                created_at, updated_at
            )
            VALUES (
                'Racoes Demo', 'Categoria fallback para demo operacional',
                '#0F766E', 'package', true, :user_id, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {"tenant_id": tenant_id, "user_id": user_id},
        )
    )


def _ensure_fallback_products(db, *, tenant_id: str, user_id: int) -> None:
    count = _scalar(
        db,
        """
        SELECT count(*) FROM produtos
        WHERE tenant_id = :tenant_id AND COALESCE(ativo, true) = true
          AND COALESCE(is_sellable, true) = true
          AND deleted_at IS NULL
        """,
        {"tenant_id": tenant_id},
    )
    if int(count or 0) >= 4:
        return

    category_id = _ensure_demo_product_category(db, tenant_id=tenant_id, user_id=user_id)
    products = [
        ("DEMO-RACAO-10KG", "Racao Premium Adulto 10kg", Decimal("128.00"), Decimal("189.90")),
        ("DEMO-RACAO-FILHOTE", "Racao Filhote Frango 3kg", Decimal("42.00"), Decimal("69.90")),
        ("DEMO-PETISCO-120G", "Petisco Natural 120g", Decimal("10.00"), Decimal("24.90")),
        ("DEMO-SHAMPOO-500ML", "Shampoo Neutro 500ml", Decimal("18.00"), Decimal("39.90")),
        ("DEMO-COLEIRA-M", "Coleira Ajustavel M", Decimal("22.00"), Decimal("49.90")),
        ("DEMO-AREIA-4KG", "Areia Higienica 4kg", Decimal("16.00"), Decimal("32.90")),
    ]
    for code, name, cost, price in products:
        exists = _scalar(
            db,
            """
            SELECT id FROM produtos
            WHERE tenant_id = :tenant_id AND lower(trim(codigo)) = lower(:code)
            LIMIT 1
            """,
            {"tenant_id": tenant_id, "code": code},
        )
        if exists:
            continue
        db.execute(
            text(
                """
                INSERT INTO produtos (
                    codigo, nome, tipo, situacao, tipo_produto, is_parent,
                    is_sellable, categoria_id, preco_custo, preco_venda,
                    preco_ecommerce, preco_app, estoque_atual, estoque_minimo,
                    estoque_fisico, estoque_ecommerce, unidade, classificacao_racao,
                    categoria_racao, peso_embalagem, auto_classificar_nome,
                    anunciar_ecommerce, anunciar_app, ativo, user_id, tenant_id,
                    created_at, updated_at
                )
                VALUES (
                    :code, :name, 'produto', true, 'SIMPLES', false,
                    true, :category_id, :cost, :price,
                    :price, :price, 30, 5,
                    24, 6, 'UN', 'premium',
                    'cao', 10, true,
                    true, true, true, :user_id, :tenant_id,
                    now(), now()
                )
                """
            ),
            {
                "code": code,
                "name": name,
                "category_id": category_id,
                "cost": cost,
                "price": price,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )


def _has_enough_real_products(db, *, tenant_id: str) -> bool:
    count = _scalar(
        db,
        """
        SELECT count(*) FROM produtos
        WHERE tenant_id = :tenant_id
          AND COALESCE(ativo, true) = true
          AND COALESCE(is_sellable, true) = true
          AND deleted_at IS NULL
          AND COALESCE(tipo_produto, 'SIMPLES') <> 'PAI'
          AND codigo NOT ILIKE 'DEMO-%'
        """,
        {"tenant_id": tenant_id},
    )
    return int(count or 0) >= 4


def _deactivate_demo_fallback_products(db, *, tenant_id: str) -> None:
    db.execute(
        text(
            """
            UPDATE produtos
            SET ativo = false,
                anunciar_ecommerce = false,
                anunciar_app = false,
                updated_at = now()
            WHERE tenant_id = :tenant_id
              AND codigo ILIKE 'DEMO-%'
            """
        ),
        {"tenant_id": tenant_id},
    )


def _extract_package_weight_kg(name: str) -> Decimal | None:
    match = re.search(r"(\d+(?:[,.]\d+)?)\s*(kg|kilo|g|gr)\b", name.lower())
    if not match:
        return None

    amount = Decimal(match.group(1).replace(",", "."))
    unit = match.group(2)
    if unit in {"g", "gr"}:
        return money(amount / Decimal("1000"))
    return money(amount)


def _demo_price_profile_for_product(
    product: dict[str, Any], idx: int
) -> tuple[Decimal, Decimal]:
    name = str(product.get("nome") or "")
    normalized_name = name.lower()
    weight_kg = _extract_package_weight_kg(name)
    is_ration = "racao" in normalized_name or "ração" in normalized_name

    if is_ration and weight_kg:
        if weight_kg >= Decimal("18"):
            prices = [Decimal("219.90"), Decimal("239.90"), Decimal("249.90")]
        elif weight_kg >= Decimal("14"):
            prices = [Decimal("169.90"), Decimal("189.90"), Decimal("199.90")]
        elif weight_kg >= Decimal("10"):
            prices = [Decimal("129.90"), Decimal("149.90"), Decimal("159.90")]
        elif weight_kg >= Decimal("5"):
            prices = [Decimal("89.90"), Decimal("99.90"), Decimal("109.90")]
        elif weight_kg >= Decimal("2"):
            prices = [Decimal("44.90"), Decimal("49.90"), Decimal("59.90")]
        else:
            prices = [Decimal("24.90"), Decimal("29.90"), Decimal("34.90")]
        price = prices[idx % len(prices)]
        return money(price * Decimal("0.62")), money(price)

    if weight_kg and weight_kg < Decimal("1"):
        prices = [Decimal("19.90"), Decimal("24.90"), Decimal("34.90"), Decimal("49.90")]
        price = prices[idx % len(prices)]
        return money(price * Decimal("0.48")), money(price)

    cost, price = DEMO_PRICE_PROFILES[idx % len(DEMO_PRICE_PROFILES)]
    return money(cost), money(price)


def _product_pool(db, *, tenant_id: str, user_id: int) -> list[dict[str, Any]]:
    _ensure_fallback_products(db, tenant_id=tenant_id, user_id=user_id)
    has_real_catalog = _has_enough_real_products(db, tenant_id=tenant_id)
    if has_real_catalog:
        _deactivate_demo_fallback_products(db, tenant_id=tenant_id)
    real_product_filter = "AND codigo NOT ILIKE 'DEMO-%'" if has_real_catalog else ""
    products = _all_mappings(
        db,
        f"""
        SELECT id, codigo, nome,
               COALESCE(NULLIF(preco_venda, 0), NULLIF(preco_app, 0), NULLIF(preco_ecommerce, 0), 49.90) AS preco_venda,
               COALESCE(NULLIF(preco_custo, 0), 24.90) AS preco_custo,
               COALESCE(estoque_atual, 0) AS estoque_atual
        FROM produtos
        WHERE tenant_id = :tenant_id
          AND COALESCE(ativo, true) = true
          AND COALESCE(is_sellable, true) = true
          AND deleted_at IS NULL
          AND COALESCE(tipo_produto, 'SIMPLES') <> 'PAI'
          {real_product_filter}
        ORDER BY
          CASE
            WHEN nome ILIKE '%racao%' OR nome ILIKE '%ração%' OR classificacao_racao IS NOT NULL OR categoria_racao IS NOT NULL THEN 0
            ELSE 1
          END,
          nome,
          id
        LIMIT 50
        """,
        {"tenant_id": tenant_id},
    )
    for idx, product in enumerate(products):
        cost, price = _demo_price_profile_for_product(product, idx)
        final_cost = money(cost)
        final_price = money(price)
        baseline = Decimal("32") + Decimal(idx * 4)
        db.execute(
            text(
                """
                UPDATE produtos
                SET preco_custo = :cost,
                    preco_venda = :price,
                    preco_ecommerce = COALESCE(preco_ecommerce, :price),
                    preco_app = COALESCE(preco_app, :price),
                    estoque_atual = :baseline,
                    estoque_fisico = :fisico,
                    estoque_ecommerce = :ecommerce,
                    anunciar_ecommerce = true,
                    anunciar_app = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "id": product["id"],
                "cost": final_cost,
                "price": final_price,
                "baseline": baseline,
                "fisico": baseline - Decimal("8"),
                "ecommerce": Decimal("8"),
            },
        )
        product["preco_custo"] = final_cost
        product["preco_venda"] = final_price
        product["baseline"] = baseline
        product["sold_qty"] = Decimal("0")
    return products


def _sale_items(products: list[dict[str, Any]], scenario: SaleScenario) -> list[dict[str, Any]]:
    items = []
    for idx, qty in scenario.items:
        product = products[idx % len(products)]
        unit_price = money(product["preco_venda"])
        subtotal = money(unit_price * qty)
        items.append(
            {
                "product": product,
                "qty": qty,
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )
    return items


def _discount_for(scenario: SaleScenario, subtotal: Decimal) -> Decimal:
    if scenario.discount_percent:
        return money(subtotal * scenario.discount_percent / Decimal("100"))
    return money(scenario.discount_value)


def _payment_profile(support: dict[str, Any], key: str) -> dict[str, Any]:
    payment_id = support["payments"][key]
    return _PAYMENT_PROFILES[key] | {"id": payment_id}


_PAYMENT_PROFILES = {
    "dinheiro": {
        "label": "dinheiro",
        "fee_percent": Decimal("0"),
        "fee_fixed": Decimal("0"),
        "due_days": 0,
        "bank": "cash",
    },
    "pix": {
        "label": "pix",
        "fee_percent": Decimal("0"),
        "fee_fixed": Decimal("0"),
        "due_days": 0,
        "bank": "main",
    },
    "debito": {
        "label": "Cartao de debito",
        "fee_percent": Decimal("1.89"),
        "fee_fixed": Decimal("0"),
        "due_days": 1,
        "bank": "main",
    },
    "credito": {
        "label": "Cartao de credito",
        "fee_percent": Decimal("3.49"),
        "fee_fixed": Decimal("0"),
        "due_days": 30,
        "bank": "main",
    },
}


def _insert_cashier(
    db,
    *,
    tenant_id: str,
    user_id: int,
    user_name: str,
    bank_cash_id: int,
    base_date: date,
) -> int:
    opened_at = datetime.combine(base_date - timedelta(days=10), time(hour=8, minute=30))
    return int(
        _scalar(
            db,
            """
            INSERT INTO caixas (
                numero_caixa, usuario_id, usuario_nome, data_abertura,
                data_fechamento, valor_abertura, valor_esperado, valor_informado,
                diferenca, status, conta_origem_id, conta_origem_nome,
                observacoes_abertura, observacoes_fechamento, tenant_id,
                created_at, updated_at
            )
            VALUES (
                9901, :user_id, :user_name, :opened_at,
                NULL, 600.00, NULL, NULL,
                NULL, 'aberto', :bank_cash_id, 'Caixa Loja Demo',
                'Demo operacional - caixa para videos', NULL, :tenant_id,
                now(), now()
            )
            RETURNING id
            """,
            {
                "user_id": user_id,
                "user_name": user_name,
                "opened_at": opened_at,
                "bank_cash_id": bank_cash_id,
                "tenant_id": tenant_id,
            },
        )
    )


def _insert_sale(
    db,
    *,
    tenant_id: str,
    user_id: int,
    user_name: str,
    scenario: SaleScenario,
    items: list[dict[str, Any]],
    support: dict[str, Any],
    base_date: date,
    cashier_id: int,
) -> dict[str, Any]:
    sale_day = base_date - timedelta(days=scenario.days_ago)
    sale_dt = datetime.combine(sale_day, time(hour=10 + scenario.days_ago % 6, minute=15))
    subtotal = money(sum(item["subtotal"] for item in items))
    discount = _discount_for(scenario, subtotal)
    total = money(subtotal - discount + scenario.delivery_fee)
    cmv = money(sum(item["product"]["preco_custo"] * item["qty"] for item in items))
    received_amount = money(total * scenario.received_ratio)
    payment = _payment_profile(support, scenario.payment_key)
    card_fee = money(total * payment["fee_percent"] / Decimal("100") + payment["fee_fixed"])
    due_days = scenario.due_in_days or payment["due_days"]
    due_date = sale_day + timedelta(days=due_days)
    received_date = sale_day if scenario.received_ratio > 0 else None
    status_receivable = (
        "recebido"
        if scenario.received_ratio >= 1
        else "parcial"
        if scenario.received_ratio > 0
        else "pendente"
    )
    sale_status = "finalizada" if scenario.received_ratio >= 1 else "aberta"
    payment_record_value = total if scenario.received_ratio >= 1 else received_amount
    channel_category_key = (
        "receita_app"
        if scenario.channel == "app_mobile"
        else "receita_ecommerce"
        if scenario.channel == "ecommerce"
        else "receita_produtos"
    )
    receivable_category = support["categories"][channel_category_key]
    bank_id = support["banks"][payment["bank"]]
    client_id = support["people"][scenario.client_key]
    driver_id = support["people"]["entregador"] if scenario.delivery else None
    delivery_loja = money(scenario.delivery_fee - scenario.driver_share)
    snapshot = {
        "demo_operacional": True,
        "cmv_total": cmv,
        "taxa_cartao": card_fee,
        "taxa_entrega": scenario.delivery_fee,
        "repasse_entregador": scenario.driver_share,
        "cupom": scenario.coupon,
        "canal": scenario.channel,
    }

    sale_id = int(
        _scalar(
            db,
            """
            INSERT INTO vendas (
                numero_venda, cliente_id, vendedor_id, funcionario_id,
                subtotal, desconto_valor, desconto_percentual, cupom_code,
                cupom_discount_applied, total, tem_entrega, taxa_entrega,
                percentual_taxa_entregador, percentual_taxa_loja,
                valor_taxa_entregador, valor_taxa_loja, entregador_id,
                loja_origem, endereco_entrega, distancia_km, valor_por_km,
                observacoes_entrega, status_entrega, data_entrega,
                ordem_entrega_otimizada, observacoes, caixa_id, canal,
                conciliado_vendas, conciliado_vendas_em, status, data_venda,
                data_finalizacao, dre_gerada, data_geracao_dre,
                rentabilidade_snapshot, rentabilidade_snapshot_em,
                tipo_retirada, palavra_chave_retirada, retirado_por,
                user_id, tenant_id, created_at, updated_at
            )
            VALUES (
                :number, :client_id, :user_id, :funcionario_id,
                :subtotal, :discount, :discount_percent, :coupon,
                :coupon_discount, :total, :delivery, :delivery_fee,
                :driver_percent, :store_percent,
                :driver_share, :delivery_loja, :driver_id,
                'Loja CorePet Demo', :delivery_address, :delivery_km, 2.20,
                :delivery_obs, :delivery_status, :delivery_date,
                NULL, :observations, :cashier_id, :channel,
                :conciliado, :conciliado_em, :sale_status, :sale_dt,
                :finalized_at, true, :sale_dt,
                CAST(:snapshot AS JSON), :sale_dt,
                :tipo_retirada, :palavra_chave, :retirado_por,
                :user_id, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "number": scenario.number,
                "client_id": client_id,
                "user_id": user_id,
                "funcionario_id": support["people"]["funcionario_vendedor"],
                "subtotal": subtotal,
                "discount": discount,
                "discount_percent": scenario.discount_percent,
                "coupon": scenario.coupon,
                "coupon_discount": discount if scenario.coupon else None,
                "total": total,
                "delivery": scenario.delivery,
                "delivery_fee": scenario.delivery_fee,
                "driver_percent": money(
                    (scenario.driver_share / scenario.delivery_fee * Decimal("100"))
                    if scenario.delivery_fee
                    else Decimal("0")
                ),
                "store_percent": money(
                    (delivery_loja / scenario.delivery_fee * Decimal("100"))
                    if scenario.delivery_fee
                    else Decimal("100")
                ),
                "driver_share": scenario.driver_share,
                "delivery_loja": delivery_loja,
                "driver_id": driver_id,
                "delivery_address": _delivery_address(db, client_id),
                "delivery_km": scenario.delivery_km or None,
                "delivery_obs": "Demo operacional - entrega com rota" if scenario.delivery else None,
                "delivery_status": _sale_delivery_status(scenario.route_status),
                "delivery_date": sale_dt + timedelta(hours=2)
                if scenario.route_status == "concluida"
                else None,
                "observations": f"Demo operacional - {scenario.observations}",
                "cashier_id": cashier_id,
                "channel": scenario.channel,
                "conciliado": scenario.received_ratio >= 1,
                "conciliado_em": sale_dt if scenario.received_ratio >= 1 else None,
                "sale_status": sale_status,
                "finalized_at": sale_dt if scenario.received_ratio >= 1 else None,
                "sale_dt": sale_dt,
                "snapshot": json.dumps(snapshot, default=decimal_json),
                "tipo_retirada": "proprio" if scenario.order_id and not scenario.delivery else None,
                "palavra_chave": "core-demo" if scenario.order_id and not scenario.delivery else None,
                "retirado_por": "Cliente demo" if scenario.order_id and not scenario.delivery else None,
                "tenant_id": tenant_id,
            },
        )
    )

    for item in items:
        _insert_sale_item(
            db,
            tenant_id=tenant_id,
            sale_id=sale_id,
            item=item,
            sale_number=scenario.number,
            user_id=user_id,
            sale_dt=sale_dt,
        )

    db.execute(
        text(
            """
            INSERT INTO venda_pagamentos (
                venda_id, forma_pagamento, valor, bandeira, numero_parcelas,
                numero_transacao, numero_autorizacao, nsu_cartao,
                status_conciliacao, valor_recebido, troco, status,
                data_pagamento, created_at, tenant_id
            )
            VALUES (
                :sale_id, :payment_label, :payment_record_value, :brand, :installments,
                :transaction, :authorization, :nsu,
                :conciliation_status, :received_amount, 0, :payment_status,
                :payment_dt, now(), :tenant_id
            )
            """
        ),
        {
            "sale_id": sale_id,
            "payment_label": payment["label"],
            "total": total,
            "payment_record_value": payment_record_value,
            "brand": scenario.card_brand,
            "installments": scenario.installments,
            "transaction": f"DEMO-TX-{scenario.number[-3:]}",
            "authorization": f"DEMO-AUT-{scenario.number[-3:]}",
            "nsu": f"DEMO-NSU-{scenario.number[-3:]}" if payment["fee_percent"] else None,
            "conciliation_status": "conciliado"
            if scenario.received_ratio >= 1
            else "nao_conciliado",
            "received_amount": received_amount,
            "payment_status": "aprovado" if received_amount > 0 else "pendente",
            "payment_dt": sale_dt,
            "tenant_id": tenant_id,
        },
    )

    receivable_id = _insert_receivable(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        sale_id=sale_id,
        client_id=client_id,
        category_id=receivable_category["category_id"],
        dre_subcategory_id=receivable_category["dre_subcategory_id"],
        payment_id=payment["id"],
        scenario=scenario,
        total=total,
        discount=discount,
        received_amount=received_amount,
        sale_day=sale_day,
        due_date=due_date,
        received_date=received_date,
        status=status_receivable,
        card_fee=card_fee,
    )

    if scenario.commissioned:
        _insert_commissions_for_sale(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            sale_id=sale_id,
            scenario=scenario,
            support=support,
            total=total,
            subtotal=subtotal,
            discount=discount,
            card_fee=card_fee,
            sale_day=sale_day,
            sale_dt=sale_dt,
        )

    if received_amount > 0:
        _insert_receipt(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            receivable_id=receivable_id,
            payment_id=payment["id"],
            amount=received_amount,
            received_date=received_date or sale_day,
            scenario=scenario,
        )
        _insert_sale_baixa(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            sale_id=sale_id,
            total=total,
            received_amount=received_amount,
            payment_label=payment["label"],
            sale_dt=sale_dt,
        )
        _insert_financial_movement(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            bank_id=bank_id,
            category_id=receivable_category["category_id"],
            payment_id=payment["id"],
            kind="entrada",
            amount=received_amount,
            document=scenario.number,
            description=f"Demo operacional - recebimento {scenario.number}",
            origin_type="conta_receber",
            origin_id=receivable_id,
            movement_dt=datetime.combine(received_date or sale_day, time(hour=15)),
            origin_channel=scenario.channel,
        )
        _insert_bank_movement(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            bank_id=bank_id,
            amount=received_amount,
            kind="entrada",
            document=f"DEMO-BANK-{scenario.number[-3:]}",
            memo=f"Demo operacional recebimento {scenario.number}",
            movement_dt=datetime.combine(received_date or sale_day, time(hour=15)),
            receivable_id=receivable_id,
            category_dre_id=receivable_category["dre_subcategory_id"],
        )
        _insert_cash_movement(
            db,
            tenant_id=tenant_id,
            cashier_id=cashier_id,
            sale_id=sale_id,
            user_id=user_id,
            user_name=user_name,
            amount=received_amount,
            payment_label=payment["label"],
            document=scenario.number,
            movement_dt=sale_dt,
            description=f"Demo operacional - venda {scenario.number}",
        )
        _insert_legacy_cashflow(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            kind="receita",
            category="Venda",
            description=f"Demo operacional - recebido {scenario.number}",
            amount=received_amount,
            movement_dt=datetime.combine(received_date or sale_day, time(hour=15)),
            status="realizado",
            origin_type="demo_operacional",
            origin_id=sale_id,
        )

    if card_fee > 0:
        _insert_payable_with_payment(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            supplier_id=support["people"]["fornecedor"],
            category=support["categories"]["taxas_cartao"],
            payment_id=support["payments"]["pix"],
            bank_id=support["banks"]["main"],
            document=f"DEMO-CP-TAXA-{scenario.number[-3:]}",
            description=f"Demo operacional - Taxa de cartao {scenario.number}",
            amount=card_fee,
            issue_date=sale_day,
            due_date=due_date,
            paid=scenario.received_ratio >= 1,
            channel=scenario.channel,
        )

    if scenario.delivery:
        _insert_route(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            scenario=scenario,
            sale_id=sale_id,
            driver_id=support["people"]["entregador"],
            sale_dt=sale_dt,
            address=_delivery_address(db, client_id),
        )
        _insert_payable_with_payment(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            supplier_id=support["people"]["entregador"],
            category=support["categories"]["repasse_entrega"],
            payment_id=support["payments"]["pix"],
            bank_id=support["banks"]["main"],
            document=f"DEMO-CP-ENT-{scenario.number[-3:]}",
            description=f"Demo operacional - Repasse entrega {scenario.number}",
            amount=scenario.driver_share,
            issue_date=sale_day,
            due_date=sale_day + timedelta(days=2),
            paid=scenario.route_status == "concluida",
            channel=scenario.channel,
        )

    if scenario.order_id:
        _insert_order(
            db,
            tenant_id=tenant_id,
            scenario=scenario,
            client_id=client_id,
            total=total,
            items=items,
        )

    return {
        "sale_id": sale_id,
        "number": scenario.number,
        "total": total,
        "received": received_amount,
        "cmv": cmv,
        "card_fee": card_fee,
        "delivery_driver": scenario.driver_share,
    }


def _delivery_address(db, client_id: int) -> str:
    row = _one_mapping(
        db,
        """
        SELECT COALESCE(
            endereco_entrega,
            endereco || ', ' || numero || ' - ' || bairro || ', ' || cidade || '/' || estado
        ) AS address
        FROM clientes WHERE id = :client_id
        """,
        {"client_id": client_id},
    )
    return row["address"] if row and row["address"] else "Endereco demo"


def _sale_delivery_status(route_status: str | None) -> str | None:
    if route_status == "concluida":
        return "entregue"
    if route_status == "em_rota":
        return "em_rota"
    if route_status == "pendente":
        return "pendente"
    return None


def _insert_sale_item(
    db,
    *,
    tenant_id: str,
    sale_id: int,
    item: dict[str, Any],
    sale_number: str,
    user_id: int,
    sale_dt: datetime,
) -> None:
    product = item["product"]
    qty = item["qty"]
    unit_price = item["unit_price"]
    subtotal = item["subtotal"]
    db.execute(
        text(
            """
            INSERT INTO venda_itens (
                venda_id, tipo, produto_id, quantidade, preco_unitario,
                desconto_item, subtotal, created_at, tenant_id
            )
            VALUES (
                :sale_id, 'produto', :product_id, :qty, :unit_price,
                0, :subtotal, :created_at, :tenant_id
            )
            """
        ),
        {
            "sale_id": sale_id,
            "product_id": product["id"],
            "qty": qty,
            "unit_price": unit_price,
            "subtotal": subtotal,
            "created_at": sale_dt,
            "tenant_id": tenant_id,
        },
    )
    old_qty = money(product["baseline"] - product["sold_qty"])
    new_qty = money(old_qty - qty)
    product["sold_qty"] = money(product["sold_qty"] + qty)
    db.execute(
        text(
            """
            INSERT INTO estoque_movimentacoes (
                produto_id, tipo, motivo, quantidade, quantidade_anterior,
                quantidade_nova, custo_unitario, valor_total, estoque_origem,
                documento, referencia_id, referencia_tipo, observacao, user_id,
                created_at, updated_at, tenant_id, status
            )
            VALUES (
                :product_id, 'saida', 'venda', :qty, :old_qty,
                :new_qty, :cost, :total_cost, 'fisico',
                :document, :sale_id, 'venda',
                'Demo operacional - baixa de estoque por venda', :user_id,
                :created_at, :created_at, :tenant_id, 'confirmado'
            )
            """
        ),
        {
            "product_id": product["id"],
            "qty": qty,
            "old_qty": old_qty,
            "new_qty": new_qty,
            "cost": product["preco_custo"],
            "total_cost": money(product["preco_custo"] * qty),
            "document": sale_number,
            "sale_id": sale_id,
            "user_id": user_id,
            "created_at": sale_dt,
            "tenant_id": tenant_id,
        },
    )


def _insert_receivable(
    db,
    *,
    tenant_id: str,
    user_id: int,
    sale_id: int,
    client_id: int,
    category_id: int,
    dre_subcategory_id: int,
    payment_id: int,
    scenario: SaleScenario,
    total: Decimal,
    discount: Decimal,
    received_amount: Decimal,
    sale_day: date,
    due_date: date,
    received_date: date | None,
    status: str,
    card_fee: Decimal,
) -> int:
    liquid_estimated = money(total - card_fee)
    return int(
        _scalar(
            db,
            """
            INSERT INTO contas_receber (
                descricao, cliente_id, categoria_id, forma_pagamento_id,
                dre_subcategoria_id, canal, valor_original, valor_recebido,
                valor_desconto, valor_juros, valor_multa, valor_final,
                data_emissao, data_vencimento, data_recebimento, status,
                eh_parcelado, numero_parcela, total_parcelas, venda_id,
                documento, observacoes, beneficiario, tipo_documento,
                nsu, adquirente, conciliado, data_conciliacao,
                status_conciliacao, taxa_mdr_estimada, taxa_mdr_real,
                valor_liquido_estimado, valor_liquido_real,
                data_vencimento_estimada, data_vencimento_real,
                tipo_recebimento, data_liquidacao, user_id, created_at,
                updated_at, tenant_id
            )
            VALUES (
                :description, :client_id, :category_id, :payment_id,
                :dre_subcategory_id, :channel, :total, :received,
                :discount, 0, 0, :total,
                :sale_day, :due_date, :received_date, :status,
                :parcelado, 1, :installments, :sale_id,
                :document, :observations, :beneficiario, 'venda',
                :nsu, :adquirente, :conciliado, :data_conciliacao,
                :status_conciliacao, :taxa_mdr, :taxa_mdr,
                :liquid_estimated, :liquid_real,
                :due_date, :due_date,
                :tipo_recebimento, :data_liquidacao, :user_id, now(),
                now(), :tenant_id
            )
            RETURNING id
            """,
            {
                "description": f"Demo operacional - Receber {scenario.number}",
                "client_id": client_id,
                "category_id": category_id,
                "payment_id": payment_id,
                "dre_subcategory_id": dre_subcategory_id,
                "channel": scenario.channel,
                "total": total,
                "received": received_amount,
                "discount": discount,
                "sale_day": sale_day,
                "due_date": due_date,
                "received_date": received_date if scenario.received_ratio >= 1 else None,
                "status": status,
                "parcelado": scenario.installments > 1,
                "installments": scenario.installments,
                "sale_id": sale_id,
                "document": f"DEMO-CR-{scenario.number[-3:]}",
                "observations": f"Demo operacional - previsao/baixa {scenario.number}",
                "beneficiario": f"Cliente demo {scenario.client_key}",
                "nsu": f"DEMO-NSU-{scenario.number[-3:]}"
                if scenario.payment_key in {"debito", "credito"}
                else None,
                "adquirente": "Stone" if scenario.payment_key in {"debito", "credito"} else None,
                "conciliado": scenario.received_ratio >= 1,
                "data_conciliacao": received_date if scenario.received_ratio >= 1 else None,
                "status_conciliacao": "liquidada"
                if scenario.received_ratio >= 1
                else "confirmada_operadora"
                if scenario.received_ratio > 0
                else "prevista",
                "taxa_mdr": Decimal("3.49") if scenario.payment_key == "credito" else Decimal("1.89")
                if scenario.payment_key == "debito"
                else None,
                "liquid_estimated": liquid_estimated,
                "liquid_real": liquid_estimated if scenario.received_ratio >= 1 else None,
                "tipo_recebimento": "parcela_individual"
                if scenario.installments > 1
                else "avista",
                "data_liquidacao": received_date if scenario.received_ratio >= 1 else None,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )


def _insert_commissions_for_sale(
    db,
    *,
    tenant_id: str,
    user_id: int,
    sale_id: int,
    scenario: SaleScenario,
    support: dict[str, Any],
    total: Decimal,
    subtotal: Decimal,
    discount: Decimal,
    card_fee: Decimal,
    sale_day: date,
    sale_dt: datetime,
) -> None:
    funcionario_id = support["people"]["funcionario_vendedor"]
    tax_amount = money((total * DEFAULT_TAX_PERCENT) / Decimal("100"))
    delivery_cost = scenario.driver_share
    sale_items = _all_mappings(
        db,
        """
        SELECT vi.id,
               vi.produto_id,
               vi.quantidade,
               vi.subtotal,
               p.preco_custo,
               p.categoria_id,
               p.subcategoria
        FROM venda_itens vi
        LEFT JOIN produtos p ON p.id = vi.produto_id
        WHERE vi.tenant_id = :tenant_id
          AND vi.venda_id = :sale_id
        ORDER BY vi.id
        """,
        {"tenant_id": tenant_id, "sale_id": sale_id},
    )
    if not sale_items:
        return

    commission_total = Decimal("0.00")
    item_rows: list[int] = []
    paid_ratio = min(max(scenario.received_ratio, Decimal("0")), Decimal("1"))

    for sale_item in sale_items:
        item_subtotal = money(sale_item["subtotal"] or 0)
        ratio = (item_subtotal / subtotal) if subtotal > 0 else Decimal("0")
        item_discount = money(discount * ratio)
        item_card_fee = money(card_fee * ratio)
        item_tax = money(tax_amount * ratio)
        item_delivery = money(delivery_cost * ratio)
        full_base = money(
            max(
                item_subtotal
                - item_discount
                - item_card_fee
                - item_tax
                - item_delivery,
                Decimal("0"),
            )
        )
        full_commission = money(
            full_base * DEFAULT_COMMISSION_PERCENT / Decimal("100")
        )
        generated_commission = money(full_commission * paid_ratio)
        if generated_commission <= 0:
            continue

        row_id = int(
            _scalar(
                db,
                """
                INSERT INTO comissoes_itens (
                    venda_id, venda_item_id, funcionario_id, produto_id,
                    categoria_id, subcategoria_id, tenant_id, data_venda,
                    quantidade, valor_venda, valor_custo, tipo_calculo,
                    valor_base_calculo, percentual_comissao, valor_comissao,
                    valor_comissao_gerada, valor_base_original,
                    valor_base_comissionada, percentual_aplicado,
                    taxa_cartao_item, impostos_item, taxa_entregador_item,
                    custo_operacional_item, receita_taxa_entrega_item,
                    percentual_impostos, percentual_pago, valor_pago_referencia,
                    parcela_numero, data_pagamento, forma_pagamento, valor_pago,
                    saldo_restante, observacao_pagamento, status,
                    data_criacao, data_atualizacao, comissao_provisionada
                )
                VALUES (
                    :sale_id, :sale_item_id, :funcionario_id, :product_id,
                    :category_id, NULL, :tenant_id, :sale_day,
                    :qty, :item_subtotal, :item_cost, 'percentual_venda_liquida',
                    :base, :percent, :commission,
                    :commission, :item_subtotal,
                    :base, :percent,
                    :card_fee, :tax, :delivery,
                    0, :delivery_revenue,
                    :tax_percent, :paid_percent, :paid_ref,
                    1, :payment_date, :payment_label, :paid_ref,
                    :saldo_restante, :obs, 'pendente',
                    :created_at, :created_at, false
                )
                RETURNING id
                """,
                {
                    "sale_id": sale_id,
                    "sale_item_id": sale_item["id"],
                    "funcionario_id": funcionario_id,
                    "product_id": sale_item["produto_id"],
                    "category_id": sale_item["categoria_id"],
                    "tenant_id": tenant_id,
                    "sale_day": sale_day,
                    "qty": sale_item["quantidade"],
                    "item_subtotal": item_subtotal,
                    "item_cost": money(
                        Decimal(str(sale_item["preco_custo"] or 0))
                        * Decimal(str(sale_item["quantidade"] or 0))
                    ),
                    "base": full_base,
                    "percent": DEFAULT_COMMISSION_PERCENT,
                    "commission": generated_commission,
                    "card_fee": item_card_fee,
                    "tax": item_tax,
                    "delivery": item_delivery,
                    "delivery_revenue": money(scenario.delivery_fee * ratio),
                    "tax_percent": DEFAULT_TAX_PERCENT,
                    "paid_percent": money(paid_ratio * Decimal("100")),
                    "paid_ref": money(total * paid_ratio),
                    "payment_date": sale_day if paid_ratio > 0 else None,
                    "payment_label": _PAYMENT_PROFILES[scenario.payment_key]["label"],
                    "saldo_restante": money(full_commission - generated_commission),
                    "obs": f"Demo operacional - comissão {scenario.number}",
                    "created_at": sale_dt,
                },
            )
        )
        item_rows.append(row_id)
        commission_total = money(commission_total + generated_commission)

    if commission_total <= 0:
        return

    payable_id = _insert_payable_with_payment(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        supplier_id=funcionario_id,
        category=support["categories"]["comissoes_vendas"],
        payment_id=support["payments"]["pix"],
        bank_id=support["banks"]["main"],
        document=f"DEMO-CP-COM-{scenario.number[-3:]}",
        description=f"Demo operacional - Comissao venda {scenario.number}",
        amount=commission_total,
        issue_date=sale_day,
        due_date=sale_day + timedelta(days=7),
        paid=False,
        channel=scenario.channel,
    )

    db.execute(
        text(
            """
            UPDATE comissoes_itens
            SET comissao_provisionada = true,
                conta_pagar_id = :payable_id,
                data_provisao = :sale_day,
                data_atualizacao = now()
            WHERE tenant_id = :tenant_id
              AND id = ANY(:item_ids)
            """
        ),
        {
            "payable_id": payable_id,
            "sale_day": sale_day,
            "tenant_id": tenant_id,
            "item_ids": item_rows,
        },
    )

    db.execute(
        text(
            """
            INSERT INTO comissoes_vendas (
                venda_id, funcionario_id, conta_pagar_id, user_id, tenant_id,
                valor_venda, valor_comissao, percentual, status,
                created_at, updated_at
            )
            VALUES (
                :sale_id, :funcionario_id, :payable_id, :user_id, :tenant_id,
                :total, :commission_total, :percent, 'pendente',
                now(), now()
            )
            """
        ),
        {
            "sale_id": sale_id,
            "funcionario_id": funcionario_id,
            "payable_id": payable_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "total": total,
            "commission_total": commission_total,
            "percent": DEFAULT_COMMISSION_PERCENT,
        },
    )


def _insert_receipt(
    db,
    *,
    tenant_id: str,
    user_id: int,
    receivable_id: int,
    payment_id: int,
    amount: Decimal,
    received_date: date,
    scenario: SaleScenario,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO recebimentos (
                conta_receber_id, forma_pagamento_id, valor_recebido,
                data_recebimento, observacoes, comprovante, user_id,
                created_at, tenant_id
            )
            VALUES (
                :receivable_id, :payment_id, :amount,
                :received_date, :obs, :comprovante, :user_id,
                now(), :tenant_id
            )
            """
        ),
        {
            "receivable_id": receivable_id,
            "payment_id": payment_id,
            "amount": amount,
            "received_date": received_date,
            "obs": f"Demo operacional - recebimento {scenario.number}",
            "comprovante": f"DEMO-COMP-REC-{scenario.number[-3:]}",
            "user_id": user_id,
            "tenant_id": tenant_id,
        },
    )


def _insert_sale_baixa(
    db,
    *,
    tenant_id: str,
    user_id: int,
    sale_id: int,
    total: Decimal,
    received_amount: Decimal,
    payment_label: str,
    sale_dt: datetime,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO venda_baixas (
                venda_id, valor_baixa, valor_anterior, valor_restante,
                forma_pagamento, tipo, usuario_id, observacoes, data_baixa,
                editado, excluido, created_at, tenant_id
            )
            VALUES (
                :sale_id, :received_amount, :total, :restante,
                :payment_label, :tipo, :user_id,
                'Demo operacional - baixa de venda', :sale_dt,
                false, false, now(), :tenant_id
            )
            """
        ),
        {
            "sale_id": sale_id,
            "received_amount": received_amount,
            "total": total,
            "restante": money(total - received_amount),
            "payment_label": payment_label,
            "tipo": "baixa_total" if received_amount >= total else "baixa_parcial",
            "user_id": user_id,
            "sale_dt": sale_dt,
            "tenant_id": tenant_id,
        },
    )


def _insert_financial_movement(
    db,
    *,
    tenant_id: str,
    user_id: int,
    bank_id: int,
    category_id: int | None,
    payment_id: int | None,
    kind: str,
    amount: Decimal,
    document: str,
    description: str,
    origin_type: str,
    origin_id: int,
    movement_dt: datetime,
    origin_channel: str | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO movimentacoes_financeiras (
                data_movimento, tipo, valor, conta_bancaria_id, categoria_id,
                forma_pagamento_id, origem_tipo, origem_id, origem_venda,
                status, documento, descricao, observacoes, user_id,
                created_at, updated_at, tenant_id
            )
            VALUES (
                :movement_dt, :kind, :amount, :bank_id, :category_id,
                :payment_id, :origin_type, :origin_id, :origin_channel,
                'realizado', :document, :description,
                'Demo operacional', :user_id, now(), now(), :tenant_id
            )
            """
        ),
        {
            "movement_dt": movement_dt,
            "kind": kind,
            "amount": amount,
            "bank_id": bank_id,
            "category_id": category_id,
            "payment_id": payment_id,
            "origin_type": origin_type,
            "origin_id": origin_id,
            "origin_channel": origin_channel,
            "document": document,
            "description": description,
            "user_id": user_id,
            "tenant_id": tenant_id,
        },
    )


def _insert_bank_movement(
    db,
    *,
    tenant_id: str,
    user_id: int,
    bank_id: int,
    amount: Decimal,
    kind: str,
    document: str,
    memo: str,
    movement_dt: datetime,
    receivable_id: int | None = None,
    payable_id: int | None = None,
    supplier_id: int | None = None,
    category_dre_id: int | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO movimentacoes_bancarias (
                conta_bancaria_id, fitid, data_movimento, valor, tipo,
                memo, status_conciliacao, confianca_sugestao, tipo_vinculo,
                fornecedor_id, conta_pagar_id, conta_receber_id,
                categoria_dre_id, classificado_por, classificado_em,
                criado_em, atualizado_em, tenant_id
            )
            VALUES (
                :bank_id, :document, :movement_dt, :signed_amount, :kind,
                :memo, 'conciliado', 98, :tipo_vinculo,
                :supplier_id, :payable_id, :receivable_id,
                :category_dre_id, :user_id, now(),
                now(), now(), :tenant_id
            )
            """
        ),
        {
            "bank_id": bank_id,
            "document": document,
            "movement_dt": movement_dt,
            "signed_amount": amount if kind == "entrada" else -amount,
            "kind": kind,
            "memo": memo,
            "tipo_vinculo": "conta_receber" if receivable_id else "conta_pagar",
            "supplier_id": supplier_id,
            "payable_id": payable_id,
            "receivable_id": receivable_id,
            "category_dre_id": category_dre_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
        },
    )


def _insert_cash_movement(
    db,
    *,
    tenant_id: str,
    cashier_id: int,
    sale_id: int,
    user_id: int,
    user_name: str,
    amount: Decimal,
    payment_label: str,
    document: str,
    movement_dt: datetime,
    description: str,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO movimentacoes_caixa (
                caixa_id, tipo, valor, forma_pagamento, descricao, categoria,
                documento, venda_id, usuario_id, usuario_nome, data_movimento,
                tenant_id, created_at, updated_at
            )
            VALUES (
                :cashier_id, 'entrada', :amount, :payment_label,
                :description, 'Venda', :document, :sale_id,
                :user_id, :user_name, :movement_dt, :tenant_id, now(), now()
            )
            """
        ),
        {
            "cashier_id": cashier_id,
            "amount": amount,
            "payment_label": payment_label,
            "description": description,
            "document": document,
            "sale_id": sale_id,
            "user_id": user_id,
            "user_name": user_name,
            "movement_dt": movement_dt,
            "tenant_id": tenant_id,
        },
    )


def _insert_legacy_cashflow(
    db,
    *,
    tenant_id: str,
    user_id: int,
    kind: str,
    category: str,
    description: str,
    amount: Decimal,
    movement_dt: datetime,
    status: str,
    origin_type: str,
    origin_id: int,
    predicted_dt: datetime | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO fluxo_caixa (
                usuario_id, tipo, categoria, descricao, valor,
                data_movimentacao, data_prevista, status, origem_tipo,
                origem_id, criado_em, atualizado_em, tenant_id
            )
            VALUES (
                :user_id, :kind, :category, :description, :amount,
                :movement_dt, :predicted_dt, :status, :origin_type,
                :origin_id, now(), now(), :tenant_id
            )
            """
        ),
        {
            "user_id": user_id,
            "kind": kind,
            "category": category,
            "description": description,
            "amount": amount,
            "movement_dt": movement_dt,
            "predicted_dt": predicted_dt,
            "status": status,
            "origin_type": origin_type,
            "origin_id": origin_id,
            "tenant_id": tenant_id,
        },
    )


def _insert_route(
    db,
    *,
    tenant_id: str,
    user_id: int,
    scenario: SaleScenario,
    sale_id: int,
    driver_id: int,
    sale_dt: datetime,
    address: str,
) -> None:
    started = sale_dt + timedelta(hours=1)
    finished = started + timedelta(minutes=45) if scenario.route_status == "concluida" else None
    route_id = int(
        _scalar(
            db,
            """
            INSERT INTO rotas_entrega (
                numero, venda_id, entregador_id, endereco_destino,
                ponto_inicial_rota, ponto_final_rota, retorna_origem,
                distancia_prevista, distancia_real, custo_previsto, custo_real,
                custo_moto, taxa_entrega_cliente, valor_repasse_entregador,
                tentativas, moto_da_loja, km_inicial, km_final, status,
                created_by, data_inicio, data_conclusao, observacoes,
                tenant_id, created_at, updated_at
            )
            VALUES (
                :number, :sale_id, :driver_id, :address,
                'Av. CorePet Demo, 100 - Centro',
                'Av. CorePet Demo, 100 - Centro', true,
                :distance, :distance_real, :cost, :cost_real,
                :moto_cost, :delivery_fee, :driver_share,
                1, true, 12450.0, :km_final, :status,
                :user_id, :started, :finished, :obs,
                :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "number": scenario.route_number,
                "sale_id": sale_id,
                "driver_id": driver_id,
                "address": address,
                "distance": scenario.delivery_km,
                "distance_real": scenario.delivery_km
                if scenario.route_status == "concluida"
                else None,
                "cost": money(scenario.delivery_km * Decimal("2.20")),
                "cost_real": money(scenario.delivery_km * Decimal("2.20"))
                if scenario.route_status == "concluida"
                else None,
                "moto_cost": money(scenario.delivery_km * Decimal("0.85")),
                "delivery_fee": scenario.delivery_fee,
                "driver_share": scenario.driver_share,
                "km_final": Decimal("12450.0") + scenario.delivery_km
                if scenario.route_status == "concluida"
                else None,
                "status": scenario.route_status,
                "user_id": user_id,
                "started": started
                if scenario.route_status in {"em_rota", "concluida"}
                else None,
                "finished": finished,
                "obs": f"Demo operacional - rota {scenario.route_status}",
                "tenant_id": tenant_id,
            },
        )
    )
    db.execute(
        text(
            """
            INSERT INTO rotas_entrega_paradas (
                rota_id, venda_id, ordem, endereco, distancia_acumulada,
                tempo_acumulado, status, data_entrega, observacoes,
                km_entrega, tenant_id, created_at, updated_at
            )
            VALUES (
                :route_id, :sale_id, 1, :address, :distance,
                :seconds, :stop_status, :delivered_at,
                'Demo operacional - parada de entrega',
                :km_entrega, :tenant_id, now(), now()
            )
            """
        ),
        {
            "route_id": route_id,
            "sale_id": sale_id,
            "address": address,
            "distance": scenario.delivery_km,
            "seconds": int(float(scenario.delivery_km) * 360),
            "stop_status": "entregue"
            if scenario.route_status == "concluida"
            else "pendente",
            "delivered_at": finished,
            "km_entrega": Decimal("12450.0") + scenario.delivery_km
            if scenario.route_status == "concluida"
            else None,
            "tenant_id": tenant_id,
        },
    )


def _insert_order(
    db,
    *,
    tenant_id: str,
    scenario: SaleScenario,
    client_id: int,
    total: Decimal,
    items: list[dict[str, Any]],
) -> None:
    db.execute(
        text(
            """
            INSERT INTO pedidos (
                pedido_id, cliente_id, tenant_id, total, origem, status,
                tipo_retirada, palavra_chave_retirada, is_drive,
                payment_provider, payment_preference_id, payment_url, created_at
            )
            VALUES (
                :order_id, :client_id, :tenant_id, :total, :origin, :status,
                :tipo_retirada, :palavra_chave, false,
                'demo', :preference, :payment_url, now()
            )
            """
        ),
        {
            "order_id": scenario.order_id,
            "client_id": client_id,
            "tenant_id": tenant_id,
            "total": float(total),
            "origin": scenario.order_origin,
            "status": scenario.order_status,
            "tipo_retirada": "proprio" if not scenario.delivery else None,
            "palavra_chave": "core-demo" if not scenario.delivery else None,
            "preference": f"PREF-{scenario.order_id}",
            "payment_url": f"https://corepet.com.br/demo/pay/{scenario.order_id}",
        },
    )
    for item in items:
        db.execute(
            text(
                """
                INSERT INTO pedido_itens (
                    pedido_id, produto_id, nome, quantidade, preco_unitario,
                    subtotal, tenant_id, created_at
                )
                VALUES (
                    :order_id, :product_id, :name, :qty, :unit_price,
                    :subtotal, :tenant_id, now()
                )
                """
            ),
            {
                "order_id": scenario.order_id,
                "product_id": item["product"]["id"],
                "name": item["product"]["nome"],
                "qty": int(item["qty"]),
                "unit_price": float(item["unit_price"]),
                "subtotal": float(item["subtotal"]),
                "tenant_id": tenant_id,
            },
        )


def _insert_payable_with_payment(
    db,
    *,
    tenant_id: str,
    user_id: int,
    supplier_id: int,
    category: dict[str, Any],
    payment_id: int,
    bank_id: int,
    document: str,
    description: str,
    amount: Decimal,
    issue_date: date,
    due_date: date,
    paid: bool,
    channel: str | None,
) -> int:
    payable_id = int(
        _scalar(
            db,
            """
            INSERT INTO contas_pagar (
                descricao, fornecedor_id, categoria_id, dre_subcategoria_id,
                canal, valor_original, valor_pago, valor_desconto, valor_juros,
                valor_multa, valor_final, data_emissao, data_vencimento,
                data_pagamento, status, eh_parcelado, eh_recorrente, documento,
                observacoes, beneficiario, tipo_documento, afeta_dre,
                percentual_online, percentual_loja, user_id, created_at,
                updated_at, tenant_id
            )
            VALUES (
                :description, :supplier_id, :category_id, :dre_subcategory_id,
                :channel, :amount, :paid_amount, 0, 0,
                0, :amount, :issue_date, :due_date,
                :payment_date, :status, false, false, :document,
                'Demo operacional', :beneficiario, 'demo',
                true, :online, :loja, :user_id, now(),
                now(), :tenant_id
            )
            RETURNING id
            """,
            {
                "description": description,
                "supplier_id": supplier_id,
                "category_id": category["category_id"],
                "dre_subcategory_id": category["dre_subcategory_id"],
                "channel": channel,
                "amount": amount,
                "paid_amount": amount if paid else Decimal("0"),
                "issue_date": issue_date,
                "due_date": due_date,
                "payment_date": due_date if paid else None,
                "status": "pago" if paid else "pendente",
                "document": document,
                "beneficiario": description.replace("Demo operacional - ", ""),
                "online": 100 if channel in {"app_mobile", "ecommerce"} else 0,
                "loja": 0 if channel in {"app_mobile", "ecommerce"} else 100,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )
    if paid:
        db.execute(
            text(
                """
                INSERT INTO pagamentos (
                    conta_pagar_id, forma_pagamento_id, valor_pago,
                    data_pagamento, observacoes, comprovante, user_id,
                    created_at, tenant_id
                )
                VALUES (
                    :payable_id, :payment_id, :amount,
                    :payment_date, :obs, :comprovante, :user_id,
                    now(), :tenant_id
                )
                """
            ),
            {
                "payable_id": payable_id,
                "payment_id": payment_id,
                "amount": amount,
                "payment_date": due_date,
                "obs": "Demo operacional - pagamento efetuado",
                "comprovante": f"DEMO-COMP-PAG-{document[-3:]}",
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
        movement_dt = datetime.combine(due_date, time(hour=16))
        _insert_financial_movement(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            bank_id=bank_id,
            category_id=category["category_id"],
            payment_id=payment_id,
            kind="saida",
            amount=amount,
            document=document,
            description=description,
            origin_type="conta_pagar",
            origin_id=payable_id,
            movement_dt=movement_dt,
            origin_channel=channel,
        )
        _insert_bank_movement(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            bank_id=bank_id,
            amount=amount,
            kind="saida",
            document=f"DEMO-BANK-{document[-3:]}",
            memo=description,
            movement_dt=movement_dt,
            payable_id=payable_id,
            supplier_id=supplier_id,
            category_dre_id=category["dre_subcategory_id"],
        )
        _insert_legacy_cashflow(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            kind="despesa",
            category="Conta a pagar",
            description=description,
            amount=amount,
            movement_dt=movement_dt,
            status="realizado",
            origin_type="demo_operacional",
            origin_id=payable_id,
        )
    else:
        _insert_legacy_cashflow(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            kind="despesa",
            category="Conta a pagar",
            description=description,
            amount=amount,
            movement_dt=datetime.combine(issue_date, time(hour=10)),
            predicted_dt=datetime.combine(due_date, time(hour=10)),
            status="previsto",
            origin_type="demo_operacional",
            origin_id=payable_id,
        )
    return payable_id


def _insert_fixed_payables(
    db,
    *,
    tenant_id: str,
    user_id: int,
    support: dict[str, Any],
    base_date: date,
) -> list[int]:
    result = []
    for payable in build_fixed_payables():
        issue = base_date - timedelta(days=payable.days_ago)
        due = issue + timedelta(days=payable.due_in_days)
        result.append(
            _insert_payable_with_payment(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                supplier_id=support["people"][payable.supplier_key],
                category=support["categories"][payable.category_key],
                payment_id=support["payments"]["pix"],
                bank_id=support["banks"]["main"],
                document=payable.document,
                description=payable.description,
                amount=money(payable.amount),
                issue_date=issue,
                due_date=due,
                paid=payable.paid,
                channel=payable.channel,
            )
        )
    return result


def _insert_stock_purchase_movements(
    db,
    *,
    tenant_id: str,
    user_id: int,
    products: Iterable[dict[str, Any]],
    base_date: date,
) -> None:
    movement_dt = datetime.combine(base_date - timedelta(days=12), time(hour=9))
    for idx, product in enumerate(list(products)[:6]):
        qty = Decimal("10") + Decimal(idx * 2)
        old_qty = money(product["baseline"])
        new_qty = money(old_qty + qty)
        product["baseline"] = new_qty
        db.execute(
            text(
                """
                INSERT INTO estoque_movimentacoes (
                    produto_id, tipo, motivo, quantidade, quantidade_anterior,
                    quantidade_nova, custo_unitario, valor_total,
                    estoque_destino, documento, referencia_tipo, observacao,
                    user_id, created_at, updated_at, tenant_id, status
                )
                VALUES (
                    :product_id, 'entrada', 'compra', :qty, :old_qty,
                    :new_qty, :cost, :total_cost,
                    'fisico', 'DEMO-COMPRA-ESTOQUE', 'compra',
                    'Demo operacional - entrada por compra',
                    :user_id, :created_at, :created_at, :tenant_id, 'confirmado'
                )
                """
            ),
            {
                "product_id": product["id"],
                "qty": qty,
                "old_qty": old_qty,
                "new_qty": new_qty,
                "cost": product["preco_custo"],
                "total_cost": money(product["preco_custo"] * qty),
                "user_id": user_id,
                "created_at": movement_dt,
                "tenant_id": tenant_id,
            },
        )


def _finalize_product_stock(db, *, tenant_id: str, products: Iterable[dict[str, Any]]) -> None:
    for product in products:
        final_qty = money(product["baseline"] - product["sold_qty"])
        db.execute(
            text(
                """
                UPDATE produtos
                SET estoque_atual = :final_qty,
                    estoque_fisico = GREATEST(:final_qty - 8, 0),
                    estoque_ecommerce = LEAST(:final_qty, 8),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :product_id
                """
            ),
            {
                "final_qty": final_qty,
                "tenant_id": tenant_id,
                "product_id": product["id"],
            },
        )


def _summarize(db, *, tenant_id: str) -> dict[str, Any]:
    rows = _all_mappings(
        db,
        """
        SELECT 'vendas' AS key, count(*)::int AS value
        FROM vendas WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'
        UNION ALL
        SELECT 'pedidos', count(*)::int
        FROM pedidos WHERE tenant_id = :tenant_id AND pedido_id LIKE 'DEMO-%'
        UNION ALL
        SELECT 'contas_receber', count(*)::int
        FROM contas_receber WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%'
        UNION ALL
        SELECT 'recebimentos', count(*)::int
        FROM recebimentos WHERE tenant_id = :tenant_id
          AND conta_receber_id IN (SELECT id FROM contas_receber WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%')
        UNION ALL
        SELECT 'contas_pagar', count(*)::int
        FROM contas_pagar WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%'
        UNION ALL
        SELECT 'pagamentos', count(*)::int
        FROM pagamentos WHERE tenant_id = :tenant_id
          AND conta_pagar_id IN (SELECT id FROM contas_pagar WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%')
        UNION ALL
        SELECT 'rotas_entrega', count(*)::int
        FROM rotas_entrega WHERE tenant_id = :tenant_id AND numero LIKE 'DEMO-ROT-%'
        UNION ALL
        SELECT 'estoque_movimentacoes', count(*)::int
        FROM estoque_movimentacoes WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%'
        UNION ALL
        SELECT 'movimentacoes_financeiras', count(*)::int
        FROM movimentacoes_financeiras WHERE tenant_id = :tenant_id AND documento LIKE 'DEMO-%'
        UNION ALL
        SELECT 'fluxo_caixa', count(*)::int
        FROM fluxo_caixa WHERE tenant_id = :tenant_id AND origem_tipo = 'demo_operacional'
        """,
        {"tenant_id": tenant_id},
    )
    counts = {row["key"]: row["value"] for row in rows}
    totals = _one_mapping(
        db,
        """
        SELECT
          COALESCE(sum(total), 0)::numeric(12,2) AS venda_total,
          COALESCE(sum(desconto_valor), 0)::numeric(12,2) AS descontos,
          COALESCE(sum(taxa_entrega), 0)::numeric(12,2) AS taxas_entrega
        FROM vendas
        WHERE tenant_id = :tenant_id AND numero_venda LIKE 'DEMO-VEN-%'
        """,
        {"tenant_id": tenant_id},
    )
    return {"counts": counts, "totals": totals or {}}


def apply_operational_seed(
    db,
    *,
    target_email: str,
    source_email: str,
    base_date: date,
    dry_run: bool,
    skip_catalog_import: bool,
) -> dict[str, Any]:
    context = _resolve_tenant_context(db, target_email)
    tenant_id = context["tenant_id"]
    user_id = int(context["user_id"])
    _set_tenant_context(db, tenant_id)

    catalog_result = _maybe_import_catalog(
        db=db,
        source_email=source_email,
        target_tenant_id=tenant_id,
        user_id=user_id,
        dry_run=dry_run,
        skip=skip_catalog_import,
    )
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "tenant_email": context["email"],
            "tenant_id": tenant_id,
            "catalog_import": catalog_result,
            "sales_scenarios": [asdict(s) for s in build_demo_scenarios()],
            "fixed_payables": [asdict(p) for p in build_fixed_payables()],
        }

    _cleanup_previous_demo(db, tenant_id=tenant_id)
    support = _ensure_support_data(
        db, tenant_id=tenant_id, user_id=user_id, base_date=base_date
    )
    products = _product_pool(db, tenant_id=tenant_id, user_id=user_id)
    _insert_stock_purchase_movements(
        db, tenant_id=tenant_id, user_id=user_id, products=products, base_date=base_date
    )
    cashier_id = _insert_cashier(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        user_name=context["user_name"],
        bank_cash_id=support["banks"]["cash"],
        base_date=base_date,
    )
    sales = []
    for scenario in build_demo_scenarios():
        sales.append(
            _insert_sale(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                user_name=context["user_name"],
                scenario=scenario,
                items=_sale_items(products, scenario),
                support=support,
                base_date=base_date,
                cashier_id=cashier_id,
            )
        )

    fixed_payable_ids = _insert_fixed_payables(
        db, tenant_id=tenant_id, user_id=user_id, support=support, base_date=base_date
    )
    _finalize_product_stock(db, tenant_id=tenant_id, products=products)

    summary = _summarize(db, tenant_id=tenant_id)
    return {
        "ok": True,
        "dry_run": False,
        "tenant_email": context["email"],
        "tenant_id": tenant_id,
        "catalog_import": catalog_result,
        "sales": sales,
        "fixed_payables": fixed_payable_ids,
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    dry_run = not args.apply
    try:
        base_date = date.fromisoformat(args.base_date)
    except ValueError:
        return _fail("--base-date deve estar no formato YYYY-MM-DD.", dry_run=dry_run)

    environment = _environment_name()
    try:
        assert_safe_environment(
            apply=args.apply,
            environment=environment,
            allow_production_apply=args.allow_production_apply,
        )
    except ValueError as exc:
        return _fail(str(exc), dry_run=dry_run)

    # Import the app only when the CLI really runs against a database.
    import app.db.base  # noqa: F401
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        result = apply_operational_seed(
            db,
            target_email=args.target_email,
            source_email=args.source_email,
            base_date=base_date,
            dry_run=dry_run,
            skip_catalog_import=args.skip_catalog_import,
        )
        if args.apply:
            db.commit()
        else:
            db.rollback()
        print(json.dumps(result, ensure_ascii=False, indent=2, default=decimal_json))
        return 0
    except Exception as exc:
        db.rollback()
        return _fail(str(exc), dry_run=dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
