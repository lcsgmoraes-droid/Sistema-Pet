"""Seed an operational demo tenant for sales, finance, stock, delivery and RH.

Default mode is dry-run. Use --apply to persist data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path


if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))


from app.scripts.seed_demo_operacional_accounting import (  # noqa: E402
    _ensure_accounting_setup,
    _ensure_dre_subcategory,
    _ensure_financial_category,
)
from app.scripts.seed_demo_operacional_catalog import (  # noqa: E402
    _cleanup_previous_demo,
    _demo_price_profile_for_product,
    _deactivate_demo_fallback_products,
    _ensure_demo_product_category,
    _ensure_fallback_products,
    _extract_package_weight_kg,
    _has_enough_real_products,
    _product_pool,
    _sale_items,
)
from app.scripts.seed_demo_operacional_data import (  # noqa: E402
    CENT,
    DEFAULT_COMMISSION_PERCENT,
    DEFAULT_SOURCE_EMAIL,
    DEFAULT_TARGET_EMAIL,
    DEFAULT_TAX_PERCENT,
    DEMO_PRICE_PROFILES,
    PRODUCTION_ENVS,
    FixedPayable,
    SaleScenario,
    build_demo_scenarios,
    build_fixed_payables,
    decimal_json,
    money,
)
from app.scripts.seed_demo_operacional_db import (  # noqa: E402
    _all_mappings,
    _maybe_import_catalog,
    _one_mapping,
    _resolve_source_tenant_id,
    _resolve_tenant_context,
    _scalar,
    _set_tenant_context,
)
from app.scripts.seed_demo_operacional_logistics import (  # noqa: E402
    _insert_order,
    _insert_route,
)
from app.scripts.seed_demo_operacional_movements import (  # noqa: E402
    _finalize_product_stock,
    _insert_bank_movement,
    _insert_cash_movement,
    _insert_financial_movement,
    _insert_fixed_payables,
    _insert_legacy_cashflow,
    _insert_payable_with_payment,
    _insert_stock_purchase_movements,
)
from app.scripts.seed_demo_operacional_payments import (  # noqa: E402
    _PAYMENT_PROFILES,
    _ensure_bank_account,
    _ensure_commission_configuration,
    _ensure_payment_method,
    _ensure_tax_configuration,
)
from app.scripts.seed_demo_operacional_runner import (  # noqa: E402
    _summarize,
    apply_operational_seed,
)
from app.scripts.seed_demo_operacional_sales_core import (  # noqa: E402
    _delivery_address,
    _discount_for,
    _insert_cashier,
    _insert_sale,
    _payment_profile,
    _sale_delivery_status,
)
from app.scripts.seed_demo_operacional_sales_finance import (  # noqa: E402
    _insert_commissions_for_sale,
    _insert_receipt,
    _insert_receivable,
    _insert_sale_baixa,
    _insert_sale_item,
)
from app.scripts.seed_demo_operacional_support import (  # noqa: E402
    _ensure_cargo,
    _ensure_delivery_config,
    _ensure_person,
    _ensure_support_data,
)


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


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    environment = _environment_name()
    dry_run = not args.apply

    try:
        base_date = date.fromisoformat(args.base_date)
    except ValueError:
        return _fail("--base-date deve estar no formato YYYY-MM-DD.", dry_run=dry_run)

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
