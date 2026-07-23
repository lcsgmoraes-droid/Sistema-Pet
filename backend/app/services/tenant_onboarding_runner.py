from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.tenant_onboarding_catalog_copies import (
    _copy_named_options,
    _copy_package_weights,
    _copy_pet_breeds,
    _copy_pet_species,
    _copy_product_categories,
    _copy_product_departments,
    _copy_products,
)
from app.services.tenant_onboarding_contract import (
    _load_template_items,
    ensure_builtin_templates,
)
from app.services.tenant_onboarding_core import (
    OnboardingResult,
    _enforce_required_onboarding,
    _tables_ready_or_warn,
    _warn_missing_template_infra_for_strict,
)
from app.services.tenant_onboarding_financial_copies import (
    _copy_bank_accounts,
    _copy_dre_categories,
    _copy_dre_subcategories,
    _copy_expense_types,
    _copy_financial_categories,
    _copy_payment_methods,
)
from app.services.tenant_onboarding_item_installs import _record_install
from app.services.tenant_onboarding_sql import _items_by_type
from app.services.tenant_onboarding_vet_copies import _copy_vet_procedures


def _run_onboarding_steps(
    db: Session,
    tenant_id_str: str,
    user_id_int: int,
    bundle_code: str,
    bundle_version: str,
    dry_run: bool,
    include_products: bool,
    strict_required: bool,
    result: OnboardingResult,
) -> dict[str, Any]:
    if not dry_run:
        ensure_builtin_templates(db)
    if strict_required and not dry_run:
        _warn_missing_template_infra_for_strict(db, result)

    items, source = _load_template_items(db, bundle_code, bundle_version)
    result.template_source = source

    if _tables_ready_or_warn(db, result, "formas de pagamento", ("formas_pagamento",)):
        _copy_payment_methods(
            db,
            _items_by_type(items, "payment_method"),
            tenant_id_str,
            user_id_int,
            result,
        )

    if _tables_ready_or_warn(db, result, "contas bancarias", ("contas_bancarias",)):
        _copy_bank_accounts(
            db,
            _items_by_type(items, "bank_account"),
            tenant_id_str,
            user_id_int,
            result,
        )

    pet_species_ids: dict[str, int] = {}
    if _tables_ready_or_warn(db, result, "especies de pets", ("especies",)):
        pet_species_ids = _copy_pet_species(
            db,
            _items_by_type(items, "pet_species"),
            tenant_id_str,
            result,
        )
    if _tables_ready_or_warn(db, result, "racas de pets", ("racas", "especies")):
        _copy_pet_breeds(
            db,
            _items_by_type(items, "pet_breed"),
            tenant_id_str,
            result,
            pet_species_ids,
        )

    category_ids: dict[str, int] = {}
    subcategory_ids: dict[str, int] = {}
    if _tables_ready_or_warn(
        db,
        result,
        "estrutura DRE",
        ("dre_categorias", "dre_subcategorias"),
    ):
        category_ids = _copy_dre_categories(
            db,
            _items_by_type(items, "dre_category"),
            tenant_id_str,
            result,
        )
        subcategory_ids = _copy_dre_subcategories(
            db,
            _items_by_type(items, "dre_subcategory"),
            tenant_id_str,
            result,
            category_ids,
        )

    if _tables_ready_or_warn(
        db, result, "categorias financeiras", ("categorias_financeiras",)
    ):
        _copy_financial_categories(
            db,
            _items_by_type(items, "financial_category"),
            tenant_id_str,
            user_id_int,
            result,
            subcategory_ids,
        )
    if _tables_ready_or_warn(db, result, "tipos de despesa", ("tipo_despesas",)):
        _copy_expense_types(
            db,
            _items_by_type(items, "expense_type"),
            tenant_id_str,
            result,
            subcategory_ids,
        )

    department_ids: dict[str, int] = {}
    product_category_ids: dict[str, int] = {}
    if _tables_ready_or_warn(
        db, result, "departamentos de produtos", ("departamentos",)
    ):
        department_ids = _copy_product_departments(
            db,
            _items_by_type(items, "product_department"),
            tenant_id_str,
            user_id_int,
            result,
        )
    if _tables_ready_or_warn(db, result, "categorias de produtos", ("categorias",)):
        product_category_ids = _copy_product_categories(
            db,
            _items_by_type(items, "product_category"),
            tenant_id_str,
            user_id_int,
            result,
            department_ids,
        )

    ration_option_sections = (
        ("linhas de racao", "linhas_racao", "ration_line", "ration_lines"),
        ("portes de animal", "portes_animal", "animal_size", "animal_sizes"),
        ("fases/publicos de racao", "fases_publico", "life_stage", "life_stages"),
        (
            "tratamentos de racao",
            "tipos_tratamento",
            "treatment_type",
            "treatment_types",
        ),
        (
            "sabores/proteinas de racao",
            "sabores_proteina",
            "protein_flavor",
            "protein_flavors",
        ),
    )
    for section_name, table_name, item_type, result_key in ration_option_sections:
        if _tables_ready_or_warn(db, result, section_name, (table_name,)):
            _copy_named_options(
                db,
                _items_by_type(items, item_type),
                tenant_id_str,
                result,
                table_name,
                result_key,
            )

    if _tables_ready_or_warn(
        db, result, "apresentacoes de peso", ("apresentacoes_peso",)
    ):
        _copy_package_weights(
            db,
            _items_by_type(items, "package_weight"),
            tenant_id_str,
            result,
        )

    if _tables_ready_or_warn(
        db,
        result,
        "procedimentos veterinarios",
        ("vet_catalogo_procedimentos",),
    ):
        _copy_vet_procedures(
            db,
            _items_by_type(items, "vet_procedure"),
            tenant_id_str,
            result,
        )

    if include_products:
        if _tables_ready_or_warn(db, result, "produtos opcionais", ("produtos",)):
            _copy_products(
                db,
                _items_by_type(items, "product_reference"),
                tenant_id_str,
                user_id_int,
                result,
                department_ids,
                product_category_ids,
            )

    if not dry_run:
        _record_install(db, tenant_id_str, user_id_int, result)

    if strict_required and not dry_run:
        _enforce_required_onboarding(result)

    return result.to_dict()
