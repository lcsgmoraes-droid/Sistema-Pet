"""Top-level runner for the operational demo seed."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from app.scripts.seed_demo_operacional_catalog import (
    _cleanup_previous_demo,
    _product_pool,
    _sale_items,
)
from app.scripts.seed_demo_operacional_data import (
    build_demo_scenarios,
    build_fixed_payables,
)
from app.scripts.seed_demo_operacional_db import (
    _all_mappings,
    _maybe_import_catalog,
    _one_mapping,
    _resolve_tenant_context,
    _set_tenant_context,
)
from app.scripts.seed_demo_operacional_movements import (
    _finalize_product_stock,
    _insert_fixed_payables,
    _insert_stock_purchase_movements,
)
from app.scripts.seed_demo_operacional_sales_core import _insert_cashier, _insert_sale
from app.scripts.seed_demo_operacional_support import _ensure_support_data


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
