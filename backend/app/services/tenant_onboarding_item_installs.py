from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.tenant_onboarding_core import (
    OnboardingResult,
    TenantOnboardingError,
    _table_exists,
)
from app.services.tenant_onboarding_sql import _scalar
from app.services.tenant_onboarding_templates import ITEM_INSTALL_TARGET_TABLES
from app.template_models import (
    TenantTemplateInstall,
    TenantTemplateItemInstall,
)


def _item_install_tables_ready(db: Session) -> bool:
    return _table_exists(db, "tenant_template_item_installs")


def _ensure_known_target_table(target_table: str) -> None:
    if target_table not in ITEM_INSTALL_TARGET_TABLES:
        raise TenantOnboardingError(
            f"Tabela alvo de template nao permitida: {target_table}."
        )


def _get_template_item_install(
    db: Session,
    tenant_id: str,
    result: OnboardingResult,
    item: dict[str, Any],
) -> TenantTemplateItemInstall | None:
    if not _item_install_tables_ready(db):
        return None

    tenant_uuid = uuid.UUID(tenant_id)
    return (
        db.query(TenantTemplateItemInstall)
        .filter(
            TenantTemplateItemInstall.tenant_id == tenant_uuid,
            TenantTemplateItemInstall.bundle_code == result.bundle_code,
            TenantTemplateItemInstall.bundle_version == result.bundle_version,
            TenantTemplateItemInstall.item_type == item["item_type"],
            TenantTemplateItemInstall.template_code == item["template_code"],
        )
        .first()
    )


def _mapped_template_row_id(
    db: Session,
    tenant_id: str,
    result: OnboardingResult,
    item: dict[str, Any],
    target_table: str,
) -> int | None:
    _ensure_known_target_table(target_table)
    install = _get_template_item_install(db, tenant_id, result, item)
    if install is None or install.target_id is None:
        return None
    if install.target_table != target_table:
        result.warnings.append(
            f"Template {item['template_code']} aponta para tabela inesperada: {install.target_table}."
        )
        return None

    existing_id = _scalar(
        db,
        f"""
        SELECT id
        FROM {target_table}
        WHERE {{tenant_filter}}
          AND id = :target_id
        LIMIT 1
        """,
        {"target_id": install.target_id},
        tenant_id,
    )
    if existing_id:
        return int(existing_id)

    result.warnings.append(
        f"Template {item['template_code']} tinha vinculo sem registro alvo em {target_table}."
    )
    return None


def _record_template_item_install(
    db: Session,
    tenant_id: str,
    user_id: int | None,
    result: OnboardingResult,
    item: dict[str, Any],
    target_table: str,
    target_id: Any,
) -> None:
    if result.dry_run or not target_id or not _item_install_tables_ready(db):
        return

    _ensure_known_target_table(target_table)
    tenant_uuid = uuid.UUID(tenant_id)
    install = _get_template_item_install(db, tenant_id, result, item)
    if install is None:
        db.add(
            TenantTemplateItemInstall(
                tenant_id=tenant_uuid,
                bundle_code=result.bundle_code,
                bundle_version=result.bundle_version,
                item_type=item["item_type"],
                template_code=item["template_code"],
                target_table=target_table,
                target_id=int(target_id),
                status="active",
                created_by_user_id=user_id,
            )
        )
    else:
        install.target_table = target_table
        install.target_id = int(target_id)
        install.status = "active"
        install.created_by_user_id = user_id
    db.flush()


def _record_install(
    db: Session, tenant_id: str, user_id: int, result: OnboardingResult
) -> None:
    if not _table_exists(db, "tenant_template_installs"):
        result.warnings.append(
            "Tabela tenant_template_installs ausente; auditoria de onboarding nao registrada."
        )
        return

    tenant_uuid = uuid.UUID(tenant_id)
    install = (
        db.query(TenantTemplateInstall)
        .filter(
            TenantTemplateInstall.tenant_id == tenant_uuid,
            TenantTemplateInstall.bundle_code == result.bundle_code,
            TenantTemplateInstall.bundle_version == result.bundle_version,
        )
        .first()
    )
    summary = result.to_dict()
    if install is None:
        db.add(
            TenantTemplateInstall(
                tenant_id=tenant_uuid,
                bundle_code=result.bundle_code,
                bundle_version=result.bundle_version,
                status="completed",
                dry_run=result.dry_run,
                created_by_user_id=user_id,
                summary=summary,
            )
        )
    else:
        install.status = "completed"
        install.dry_run = result.dry_run
        install.created_by_user_id = user_id
        install.summary = summary
    db.flush()
