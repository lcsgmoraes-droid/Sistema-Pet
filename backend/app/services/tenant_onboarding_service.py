from __future__ import annotations

from typing import Any

from sqlalchemy.exc import SQLAlchemyError
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
    validate_onboarding_template_contract,
)
from app.services.tenant_onboarding_core import (
    OnboardingResult,
    TenantOnboardingError,
    _normalize_tenant_id,
    _normalize_user_id,
)
from app.services.tenant_onboarding_financial_copies import (
    _copy_bank_accounts,
    _copy_dre_categories,
    _copy_dre_subcategories,
    _copy_expense_types,
    _copy_financial_categories,
    _copy_payment_methods,
)
from app.services.tenant_onboarding_item_installs import (
    _ensure_known_target_table,
    _get_template_item_install,
    _item_install_tables_ready,
    _mapped_template_row_id,
    _record_install,
    _record_template_item_install,
)
from app.services.tenant_onboarding_runner import _run_onboarding_steps
from app.services.tenant_onboarding_sql import (
    _insert_target_table,
    _items_by_type,
    _scalar as _sql_scalar,
    _sync_postgres_id_sequence,
    _execute_insert as _sql_execute_insert,
)
from app.services.tenant_onboarding_templates import (
    DEFAULT_BUNDLE_CODE,
    DEFAULT_BUNDLE_VERSION,
    REQUIRED_ONBOARDING_SECTIONS,
)
from app.utils.tenant_safe_sql import (
    execute_tenant_safe,
    execute_tenant_safe_scalar,
)


__all__ = [
    "OnboardingResult",
    "REQUIRED_ONBOARDING_SECTIONS",
    "TenantOnboardingError",
    "onboard_tenant_defaults",
    "validate_onboarding_template_contract",
]


_COMPAT_PRIVATE_REEXPORTS = (
    _copy_bank_accounts,
    _copy_dre_categories,
    _copy_dre_subcategories,
    _copy_expense_types,
    _copy_financial_categories,
    _copy_named_options,
    _copy_package_weights,
    _copy_payment_methods,
    _copy_pet_breeds,
    _copy_pet_species,
    _copy_product_categories,
    _copy_product_departments,
    _copy_products,
    _ensure_known_target_table,
    _get_template_item_install,
    _insert_target_table,
    _item_install_tables_ready,
    _items_by_type,
    _load_template_items,
    _mapped_template_row_id,
    _record_install,
    _record_template_item_install,
    _sync_postgres_id_sequence,
    ensure_builtin_templates,
)


def _scalar(db: Session, sql: str, params: dict[str, Any], tenant_id: str) -> Any:
    return _sql_scalar(
        db,
        sql,
        params,
        tenant_id,
        scalar_fn=execute_tenant_safe_scalar,
    )


def _execute_insert(
    db: Session, sql: str, params: dict[str, Any], tenant_id: str
) -> None:
    return _sql_execute_insert(
        db,
        sql,
        params,
        tenant_id,
        execute_fn=execute_tenant_safe,
    )


def onboard_tenant_defaults(
    db: Session,
    tenant_id: Any,
    user_id: Any,
    bundle_code: str = DEFAULT_BUNDLE_CODE,
    bundle_version: str = DEFAULT_BUNDLE_VERSION,
    dry_run: bool = False,
    include_products: bool = False,
    strict_required: bool = False,
) -> dict[str, Any]:
    """
    Copy system templates into tenant-owned tables.

    The operation is idempotent: existing tenant records are skipped and missing
    records are created. Products are intentionally optional and not copied by
    default because catalog data is business-specific.
    """
    tenant_id_str = _normalize_tenant_id(tenant_id)
    user_id_int = _normalize_user_id(user_id)

    result = OnboardingResult(
        tenant_id=tenant_id_str,
        bundle_code=bundle_code,
        bundle_version=bundle_version,
        dry_run=dry_run,
    )

    # As tabelas de auditoria de onboarding (tenant_template_installs / _item_installs)
    # sao TenantScoped: as queries ORM internas exigem um tenant no contexto. Estabelecemos
    # o contexto do tenant alvo aqui (salvando o anterior e restaurando no fim), para que
    # TODO caller funcione sem setar manualmente: o signup (que ja seta o mesmo tenant) fica
    # intacto, e o CLI run_tenant_onboarding e os testes passam a ter contexto -- sem
    # perturbar o contexto de quem chamou.
    from uuid import UUID as _UUID
    from app.tenancy.context import (
        clear_current_tenant as _clear_tenant,
        get_current_tenant as _get_tenant,
        set_current_tenant as _set_tenant,
    )

    _tenant_anterior = _get_tenant()
    _set_tenant(_UUID(tenant_id_str))
    try:
        return _run_onboarding_steps(
            db,
            tenant_id_str,
            user_id_int,
            bundle_code,
            bundle_version,
            dry_run,
            include_products,
            strict_required,
            result,
        )
    except SQLAlchemyError as exc:
        raise TenantOnboardingError(
            f"Falha no onboarding do tenant {tenant_id_str}: {exc}"
        ) from exc
    finally:
        if _tenant_anterior is not None:
            _set_tenant(_tenant_anterior)
        else:
            _clear_tenant()
