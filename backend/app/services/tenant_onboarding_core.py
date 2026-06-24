from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.services.tenant_onboarding_templates import (
    REQUIRED_ONBOARDING_SECTIONS,
    TEMPLATE_INFRA_TABLES,
)


class TenantOnboardingError(RuntimeError):
    pass


@dataclass
class OnboardingResult:
    tenant_id: str
    bundle_code: str
    bundle_version: str
    dry_run: bool
    created: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)
    would_create: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    template_source: str = "builtin"

    def bump(self, bucket: str, key: str) -> None:
        target = getattr(self, bucket)
        target[key] = target.get(key, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "bundle_code": self.bundle_code,
            "bundle_version": self.bundle_version,
            "dry_run": self.dry_run,
            "created": self.created,
            "skipped": self.skipped,
            "would_create": self.would_create,
            "warnings": self.warnings,
            "template_source": self.template_source,
        }


def _table_exists(db: Session, table_name: str) -> bool:
    return inspect(db.connection()).has_table(table_name)


def _enforce_required_onboarding(result: OnboardingResult) -> None:
    missing_sections = sorted(
        section
        for section in REQUIRED_ONBOARDING_SECTIONS
        if result.created.get(section, 0) + result.skipped.get(section, 0) <= 0
    )
    if not missing_sections and not result.warnings:
        return

    details: list[str] = []
    if missing_sections:
        details.append("secoes obrigatorias ausentes: " + ", ".join(missing_sections))
    if result.warnings:
        details.append("avisos: " + " | ".join(result.warnings))
    raise TenantOnboardingError(
        "Onboarding obrigatorio incompleto para novo tenant: " + "; ".join(details)
    )


def _warn_missing_template_infra_for_strict(
    db: Session, result: OnboardingResult
) -> None:
    missing = [
        table_name
        for table_name in TEMPLATE_INFRA_TABLES
        if not _table_exists(db, table_name)
    ]
    if missing:
        result.warnings.append(
            "Infraestrutura de templates ausente para onboarding estrito "
            f"({', '.join(missing)})."
        )


def _normalize_tenant_id(tenant_id: Any) -> str:
    if tenant_id is None or str(tenant_id).strip() == "":
        raise TenantOnboardingError("tenant_id e obrigatorio para onboarding.")
    return str(tenant_id)


def _normalize_user_id(user_id: Any) -> int:
    if user_id is None or str(user_id).strip() == "":
        raise TenantOnboardingError("user_id e obrigatorio para onboarding.")
    return int(user_id)


def _db_enum_label(
    value: Any, labels: dict[str, str], field_name: str, allow_none: bool = False
) -> str | None:
    if value is None:
        if allow_none:
            return None
        raise TenantOnboardingError(f"{field_name} e obrigatorio no template.")
    normalized = str(value).strip()
    if not normalized:
        if allow_none:
            return None
        raise TenantOnboardingError(f"{field_name} e obrigatorio no template.")
    if normalized in labels.values():
        return normalized
    mapped = labels.get(normalized.lower())
    if mapped is None:
        raise TenantOnboardingError(f"{field_name} invalido no template: {value}.")
    return mapped


def _tables_ready_or_warn(
    db: Session,
    result: OnboardingResult,
    section: str,
    table_names: tuple[str, ...],
) -> bool:
    missing = [
        table_name for table_name in table_names if not _table_exists(db, table_name)
    ]
    if not missing:
        return True

    result.warnings.append(
        f"Onboarding parcial: schema ausente para {section} ({', '.join(missing)})."
    )
    return False
