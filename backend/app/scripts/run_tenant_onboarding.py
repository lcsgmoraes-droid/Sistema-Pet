"""Run tenant onboarding defaults for an existing tenant.

Default mode is dry-run. Use --apply to persist data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text

if __package__ in {None, ""}:
    backend_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.services.tenant_onboarding_service import (
    onboard_tenant_defaults,
    validate_onboarding_template_contract,
)


PRODUCTION_ENVS = {"prod", "production"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copy global default templates into a tenant-owned setup."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--tenant-id", help="Tenant UUID to onboard.")
    target.add_argument(
        "--all-active-tenants",
        action="store_true",
        help="Run onboarding for every active tenant with an active owner user.",
    )
    target.add_argument(
        "--health-check",
        action="store_true",
        help="Summarize onboarding completeness for active tenants without applying changes.",
    )
    target.add_argument(
        "--future-tenant-check",
        action="store_true",
        help="Validate the default onboarding contract for a synthetic future tenant without reading existing tenants.",
    )
    target.add_argument(
        "--template-check",
        action="store_true",
        help="Validate global template readiness for future tenants without applying changes.",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="Admin/user id used as owner of copied rows. Required with --tenant-id.",
    )
    parser.add_argument("--bundle-code", default="petshop-br", help="Template bundle code.")
    parser.add_argument("--bundle-version", default="v1", help="Template bundle version.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist onboarding changes. Without this flag the command is dry-run only.",
    )
    parser.add_argument(
        "--include-products",
        action="store_true",
        help="Reserved for optional product import. Current phase only reports a warning.",
    )
    parser.add_argument(
        "--allow-production-apply",
        action="store_true",
        help="Allow --apply when APP_ENV/ENV/ENVIRONMENT is production/prod.",
    )
    parser.add_argument(
        "--allow-existing-tenant-apply",
        action="store_true",
        help="Allow bulk --all-active-tenants --apply. Keep disabled unless intentionally backfilling existing tenants.",
    )
    return parser


def _environment_name() -> str:
    for name in ("APP_ENV", "ENVIRONMENT", "ENV"):
        value = os.getenv(name)
        if value:
            return value.strip().lower()
    return ""


def _fail(message: str, dry_run: bool) -> int:
    print(
        json.dumps(
            {
                "ok": False,
                "error": message,
                "dry_run": dry_run,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 1


def _active_owner_condition(dialect_name: str) -> str:
    if dialect_name == "postgresql":
        return "(is_active IS NULL OR is_active IS TRUE)"
    return "(is_active IS NULL OR is_active = 1)"


def _find_active_tenants_with_owner(db) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inspector = inspect(db.connection())
    if not inspector.has_table("tenants"):
        return [], [{"tenant_id": None, "reason": "Tabela tenants ausente."}]
    if not inspector.has_table("users"):
        return [], [{"tenant_id": None, "reason": "Tabela users ausente."}]

    tenants = db.execute(
        text(
            """
            SELECT id
            FROM tenants
            WHERE status IS NULL OR lower(status) IN ('active', 'ativo')
            ORDER BY id
            """
        )
    ).mappings()

    owner_condition = _active_owner_condition(db.get_bind().dialect.name)
    targets: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for tenant in tenants:
        tenant_id = str(tenant["id"])
        owner = db.execute(
            text(
                f"""
                SELECT id
                FROM users
                WHERE CAST(tenant_id AS TEXT) = :tenant_id
                  AND {owner_condition}
                ORDER BY id
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        ).mappings().first()
        if owner is None:
            skipped.append({"tenant_id": tenant_id, "reason": "Tenant sem usuario ativo."})
            continue
        targets.append({"tenant_id": tenant_id, "user_id": int(owner["id"])})

    return targets, skipped


def _merge_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + int(value)


def _run_one(db, args, tenant_id: str, user_id: int) -> dict[str, Any]:
    return onboard_tenant_defaults(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        bundle_code=args.bundle_code,
        bundle_version=args.bundle_version,
        dry_run=not args.apply,
        include_products=args.include_products,
    )


def _run_all(db, args) -> dict[str, Any]:
    targets, skipped = _find_active_tenants_with_owner(db)
    totals = {
        "created": {},
        "skipped": {},
        "would_create": {},
    }
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for target in targets:
        try:
            result = _run_one(db, args, target["tenant_id"], target["user_id"])
            if args.apply:
                db.commit()
            else:
                db.rollback()
            results.append(result)
            _merge_counts(totals["created"], result.get("created", {}))
            _merge_counts(totals["skipped"], result.get("skipped", {}))
            _merge_counts(totals["would_create"], result.get("would_create", {}))
        except Exception as exc:
            db.rollback()
            errors.append({"tenant_id": target["tenant_id"], "error": str(exc)})

    return {
        "ok": not errors,
        "dry_run": not args.apply,
        "mode": "all_active_tenants",
        "tenant_count": len(targets),
        "skipped_tenants": skipped,
        "errors": errors,
        "totals": totals,
        "results": results,
    }


def _run_health_check(db, args) -> dict[str, Any]:
    targets, skipped = _find_active_tenants_with_owner(db)
    totals = {
        "created": {},
        "skipped": {},
        "would_create": {},
    }
    complete: list[str] = []
    incomplete: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for target in targets:
        try:
            result = _run_one(db, args, target["tenant_id"], target["user_id"])
            db.rollback()
            _merge_counts(totals["created"], result.get("created", {}))
            _merge_counts(totals["skipped"], result.get("skipped", {}))
            _merge_counts(totals["would_create"], result.get("would_create", {}))
            would_create = result.get("would_create", {})
            warnings = result.get("warnings", [])
            if would_create or warnings:
                incomplete.append(
                    {
                        "tenant_id": target["tenant_id"],
                        "would_create": would_create,
                        "warnings": warnings,
                    }
                )
            else:
                complete.append(target["tenant_id"])
        except Exception as exc:
            db.rollback()
            errors.append({"tenant_id": target["tenant_id"], "error": str(exc)})

    return {
        "ok": not errors and not incomplete,
        "dry_run": True,
        "mode": "health_check",
        "include_products": bool(args.include_products),
        "tenant_count": len(targets),
        "complete_tenants": complete,
        "complete_count": len(complete),
        "incomplete_tenants": incomplete,
        "incomplete_count": len(incomplete),
        "skipped_tenants": skipped,
        "errors": errors,
        "totals": totals,
    }


def _run_future_tenant_check(db, args) -> dict[str, Any]:
    synthetic_tenant_id = "00000000-0000-4000-8000-000000000001"
    result = onboard_tenant_defaults(
        db=db,
        tenant_id=synthetic_tenant_id,
        user_id=0,
        bundle_code=args.bundle_code,
        bundle_version=args.bundle_version,
        dry_run=True,
        include_products=args.include_products,
    )
    db.rollback()

    required_sections = {
        "payment_methods",
        "dre_categories",
        "dre_subcategories",
        "financial_categories",
        "expense_types",
        "product_departments",
        "product_categories",
    }
    would_create = result.get("would_create", {})
    missing_sections = sorted(
        section
        for section in required_sections
        if int(would_create.get(section, 0)) <= 0 and int(result.get("skipped", {}).get(section, 0)) <= 0
    )
    warnings = result.get("warnings", [])

    return {
        "ok": not missing_sections and not warnings,
        "dry_run": True,
        "mode": "future_tenant_check",
        "tenant_scope": "synthetic_future_tenant",
        "bundle_code": args.bundle_code,
        "bundle_version": args.bundle_version,
        "include_products": bool(args.include_products),
        "required_sections": sorted(required_sections),
        "missing_sections": missing_sections,
        "warnings": warnings,
        "result": {
            "template_source": result.get("template_source"),
            "would_create": would_create,
            "skipped": result.get("skipped", {}),
            "created": result.get("created", {}),
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    dry_run = not args.apply

    if args.tenant_id and args.user_id is None:
        return _fail("--user-id e obrigatorio quando --tenant-id e usado.", dry_run=dry_run)

    if args.health_check and args.apply:
        return _fail("--health-check e somente leitura; remova --apply.", dry_run=True)

    if args.future_tenant_check and args.apply:
        return _fail("--future-tenant-check e somente leitura; remova --apply.", dry_run=True)

    if args.template_check and args.apply:
        return _fail("--template-check e somente leitura; remova --apply.", dry_run=True)

    if args.all_active_tenants and args.apply and not args.allow_existing_tenant_apply:
        return _fail(
            "--all-active-tenants --apply bloqueado por padrao; use --allow-existing-tenant-apply "
            "somente se for intencional atualizar tenants existentes.",
            dry_run=False,
        )

    environment = _environment_name()
    if args.apply and environment in PRODUCTION_ENVS and not args.allow_production_apply:
        return _fail(
            "Ambiente production/prod detectado; --apply bloqueado sem --allow-production-apply.",
            dry_run=dry_run,
        )

    db = SessionLocal()
    try:
        if args.health_check:
            result = _run_health_check(db, args)
        elif args.future_tenant_check:
            result = _run_future_tenant_check(db, args)
        elif args.template_check:
            result = validate_onboarding_template_contract(
                db=db,
                bundle_code=args.bundle_code,
                bundle_version=args.bundle_version,
                include_products=args.include_products,
            )
            db.rollback()
        elif args.all_active_tenants:
            result = _run_all(db, args)
        else:
            result = _run_one(db, args, args.tenant_id, args.user_id)
            if args.apply:
                db.commit()
            else:
                db.rollback()

        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result.get("ok", True) else 1
    except Exception as exc:
        db.rollback()
        return _fail(str(exc), dry_run=dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
