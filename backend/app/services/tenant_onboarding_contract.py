from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.tenant_onboarding_core import TenantOnboardingError, _table_exists
from app.services.tenant_onboarding_templates import (
    BUILTIN_TEMPLATE_ITEMS,
    DEFAULT_BUNDLE_CODE,
    DEFAULT_BUNDLE_VERSION,
    REQUIRED_ONBOARDING_SECTIONS,
    REQUIRED_ONBOARDING_TABLES,
    REQUIRED_TEMPLATE_ITEM_TYPES,
    TEMPLATE_INFRA_TABLES,
)
from app.template_models import TemplateBundle, TemplateItem


def _template_tables_ready(db: Session) -> bool:
    return _table_exists(db, "template_bundles") and _table_exists(db, "template_items")


def ensure_builtin_templates(db: Session) -> None:
    """Create system-owned builtin templates when template tables exist."""
    if not _template_tables_ready(db):
        return

    bundle = (
        db.query(TemplateBundle)
        .filter(
            TemplateBundle.bundle_code == DEFAULT_BUNDLE_CODE,
            TemplateBundle.version == DEFAULT_BUNDLE_VERSION,
        )
        .first()
    )
    if bundle is None:
        db.add(
            TemplateBundle(
                bundle_code=DEFAULT_BUNDLE_CODE,
                version=DEFAULT_BUNDLE_VERSION,
                name="Pet Shop Brasil",
                description="Pacote padrao inicial para tenants de pet shop.",
                active=True,
            )
        )
        db.flush()

    existing_codes = {
        row[0]
        for row in db.query(TemplateItem.template_code)
        .filter(
            TemplateItem.bundle_code == DEFAULT_BUNDLE_CODE,
            TemplateItem.bundle_version == DEFAULT_BUNDLE_VERSION,
        )
        .all()
    }
    for item in BUILTIN_TEMPLATE_ITEMS:
        if item["template_code"] in existing_codes:
            continue
        db.add(
            TemplateItem(
                bundle_code=DEFAULT_BUNDLE_CODE,
                bundle_version=DEFAULT_BUNDLE_VERSION,
                item_type=item["item_type"],
                template_code=item["template_code"],
                name=item["name"],
                payload=item["payload"],
                sort_order=item["sort_order"],
                active=True,
            )
        )
    db.flush()


def _query_template_items(
    db: Session, bundle_code: str, bundle_version: str
) -> list[dict[str, Any]]:
    rows = (
        db.query(TemplateItem)
        .filter(
            TemplateItem.bundle_code == bundle_code,
            TemplateItem.bundle_version == bundle_version,
            TemplateItem.active.is_(True),
        )
        .order_by(TemplateItem.sort_order.asc(), TemplateItem.id.asc())
        .all()
    )
    return [
        {
            "item_type": row.item_type,
            "template_code": row.template_code,
            "name": row.name,
            "payload": row.payload,
            "sort_order": row.sort_order,
        }
        for row in rows
    ]


def _missing_builtin_template_items(
    db: Session, bundle_code: str, bundle_version: str
) -> list[dict[str, Any]]:
    existing_codes = {
        row[0]
        for row in db.query(TemplateItem.template_code)
        .filter(
            TemplateItem.bundle_code == bundle_code,
            TemplateItem.bundle_version == bundle_version,
        )
        .all()
    }
    return [
        item
        for item in BUILTIN_TEMPLATE_ITEMS
        if item["template_code"] not in existing_codes
    ]


def _combine_template_items(
    db: Session,
    bundle_code: str,
    bundle_version: str,
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str] | None:
    if bundle_code != DEFAULT_BUNDLE_CODE or bundle_version != DEFAULT_BUNDLE_VERSION:
        return None

    missing_builtin_items = _missing_builtin_template_items(
        db, bundle_code, bundle_version
    )
    if not items and not missing_builtin_items:
        return None

    combined = items + missing_builtin_items
    combined.sort(
        key=lambda item: (int(item.get("sort_order") or 0), item["template_code"])
    )
    source = "database" if not missing_builtin_items else "database+builtin_pending"
    return combined, source


def _load_template_items(
    db: Session, bundle_code: str, bundle_version: str
) -> tuple[list[dict[str, Any]], str]:
    if _template_tables_ready(db):
        items = _query_template_items(db, bundle_code, bundle_version)
        combined = _combine_template_items(db, bundle_code, bundle_version, items)
        if combined is not None:
            return combined
        if items:
            return items, "database"

    if bundle_code == DEFAULT_BUNDLE_CODE and bundle_version == DEFAULT_BUNDLE_VERSION:
        return list(BUILTIN_TEMPLATE_ITEMS), "builtin"

    raise TenantOnboardingError(
        f"Template bundle nao encontrado: {bundle_code}@{bundle_version}."
    )


def _count_items_by_type(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        item_type = str(item.get("item_type") or "")
        counts[item_type] = counts.get(item_type, 0) + 1
    return counts


def _template_codes_by_type(items: list[dict[str, Any]], item_type: str) -> set[str]:
    return {
        str(item.get("template_code"))
        for item in items
        if item.get("item_type") == item_type and item.get("template_code")
    }


def _validate_payload_reference(
    errors: list[str],
    item: dict[str, Any],
    payload_key: str,
    valid_codes: set[str],
    target_label: str,
) -> None:
    payload = item.get("payload") or {}
    reference = payload.get(payload_key)
    template_code = item.get("template_code")
    if not reference:
        errors.append(f"Template {template_code} sem {payload_key}.")
        return
    if str(reference) not in valid_codes:
        errors.append(
            f"Template {template_code} referencia {target_label} inexistente: "
            f"{reference}."
        )


def _find_template_dependency_errors(
    items: list[dict[str, Any]],
    include_products: bool,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    dre_category_codes = _template_codes_by_type(items, "dre_category")
    dre_subcategory_codes = _template_codes_by_type(items, "dre_subcategory")
    product_department_codes = _template_codes_by_type(items, "product_department")
    product_category_codes = _template_codes_by_type(items, "product_category")
    pet_species_codes = _template_codes_by_type(items, "pet_species")

    for item in items:
        item_type = item.get("item_type")
        payload = item.get("payload") or {}
        if item_type == "dre_subcategory":
            _validate_payload_reference(
                errors, item, "categoria_code", dre_category_codes, "dre_category"
            )
        elif item_type == "expense_type":
            _validate_payload_reference(
                errors,
                item,
                "dre_subcategory_code",
                dre_subcategory_codes,
                "dre_subcategory",
            )
        elif item_type == "financial_category":
            reference = payload.get("dre_subcategory_code")
            if reference and str(reference) not in dre_subcategory_codes:
                errors.append(
                    f"Template {item.get('template_code')} referencia "
                    f"dre_subcategory inexistente: {reference}."
                )
            elif not reference:
                warnings.append(
                    f"Template {item.get('template_code')} sem vinculo DRE opcional."
                )
        elif item_type == "product_category":
            _validate_payload_reference(
                errors,
                item,
                "departamento_code",
                product_department_codes,
                "product_department",
            )
        elif item_type == "pet_breed":
            _validate_payload_reference(
                errors,
                item,
                "species_code",
                pet_species_codes,
                "pet_species",
            )
        elif item_type == "product_reference":
            target = errors if include_products else warnings
            _validate_payload_reference(
                target,
                item,
                "departamento_code",
                product_department_codes,
                "product_department",
            )
            _validate_payload_reference(
                target,
                item,
                "categoria_code",
                product_category_codes,
                "product_category",
            )

    return errors, warnings


def validate_onboarding_template_contract(
    db: Session,
    bundle_code: str = DEFAULT_BUNDLE_CODE,
    bundle_version: str = DEFAULT_BUNDLE_VERSION,
    include_products: bool = False,
) -> dict[str, Any]:
    """
    Read-only validation for the global template bundle needed by future tenants.

    This check never creates tenants or tenant-owned rows. It validates the
    template infrastructure, required operational tables and template dependency
    graph before the strict signup onboarding path is exercised.
    """
    missing_template_tables = [
        table_name
        for table_name in TEMPLATE_INFRA_TABLES
        if not _table_exists(db, table_name)
    ]
    missing_operational_tables = {
        section: [
            table_name
            for table_name in table_names
            if not _table_exists(db, table_name)
        ]
        for section, table_names in REQUIRED_ONBOARDING_TABLES.items()
    }
    missing_operational_tables = {
        section: missing
        for section, missing in missing_operational_tables.items()
        if missing
    }
    errors: list[str] = []
    items: list[dict[str, Any]] = []
    template_source = "unavailable"

    try:
        items, template_source = _load_template_items(db, bundle_code, bundle_version)
    except TenantOnboardingError as exc:
        errors.append(str(exc))

    counts_by_type = _count_items_by_type(items)
    missing_sections = sorted(
        section
        for section, item_type in REQUIRED_TEMPLATE_ITEM_TYPES.items()
        if counts_by_type.get(item_type, 0) <= 0
    )
    product_reference_count = counts_by_type.get("product_reference", 0)

    seen_codes: dict[str, int] = {}
    for item in items:
        code = str(item.get("template_code") or "")
        seen_codes[code] = seen_codes.get(code, 0) + 1
    duplicate_template_codes = sorted(
        code for code, count in seen_codes.items() if code and count > 1
    )

    dependency_errors, dependency_warnings = _find_template_dependency_errors(
        items, include_products
    )

    builtin_pending_count = 0
    if (
        _template_tables_ready(db)
        and bundle_code == DEFAULT_BUNDLE_CODE
        and bundle_version == DEFAULT_BUNDLE_VERSION
    ):
        builtin_pending_count = len(
            _missing_builtin_template_items(db, bundle_code, bundle_version)
        )

    ok = not (
        missing_template_tables
        or missing_operational_tables
        or errors
        or missing_sections
        or duplicate_template_codes
        or dependency_errors
    )

    return {
        "ok": ok,
        "mode": "template_contract_check",
        "dry_run": True,
        "bundle_code": bundle_code,
        "bundle_version": bundle_version,
        "include_products": bool(include_products),
        "template_source": template_source,
        "template_item_counts": counts_by_type,
        "required_sections": sorted(REQUIRED_ONBOARDING_SECTIONS),
        "missing_sections": missing_sections,
        "missing_template_tables": missing_template_tables,
        "missing_operational_tables": missing_operational_tables,
        "duplicate_template_codes": duplicate_template_codes,
        "dependency_errors": dependency_errors,
        "dependency_warnings": dependency_warnings,
        "product_reference_count": product_reference_count,
        "builtin_pending_count": builtin_pending_count,
    }
