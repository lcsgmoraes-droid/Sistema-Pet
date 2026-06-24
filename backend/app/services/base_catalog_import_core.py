from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.tenancy.rls import sync_rls_tenant


DEFAULT_BASE_CATALOG_SOURCE_EMAIL = "atacadaopetpp@gmail.com"
DEFAULT_BASE_CATALOG_BUNDLE_CODE = "catalogo-base-loja-lucas"
DEFAULT_BASE_CATALOG_BUNDLE_VERSION = "v1"

ImageCopier = Callable[..., str]

SUPPORT_OPTION_TABLES = (
    ("linhas_racao", "linha_racao"),
    ("portes_animal", "porte_animal"),
    ("fases_publico", "fase_publico"),
    ("tipos_tratamento", "tipo_tratamento"),
    ("sabores_proteina", "sabor_proteina"),
    ("apresentacoes_peso", "apresentacao_peso"),
)

PRODUCT_OPERATIONAL_ZERO_FIELDS = {
    "estoque_atual",
    "estoque_minimo",
    "estoque_maximo",
    "estoque_fisico",
    "estoque_ecommerce",
    "preco_custo",
    "preco_venda",
}

PRODUCT_OPERATIONAL_NULL_FIELDS = {
    "preco_promocional",
    "promocao_inicio",
    "promocao_fim",
    "preco_ecommerce",
    "preco_ecommerce_promo",
    "preco_ecommerce_promo_inicio",
    "preco_ecommerce_promo_fim",
    "preco_app",
    "preco_app_promo",
    "preco_app_promo_inicio",
    "preco_app_promo_fim",
    "fornecedor_id",
    "localizacao",
}


class BaseCatalogImportError(RuntimeError):
    pass


@dataclass
class BaseCatalogImportResult:
    source_tenant_id: str
    target_tenant_id: str
    dry_run: bool
    bundle_code: str = DEFAULT_BASE_CATALOG_BUNDLE_CODE
    bundle_version: str = DEFAULT_BASE_CATALOG_BUNDLE_VERSION
    created: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)
    would_create: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def bump(self, bucket: str, key: str) -> None:
        target = getattr(self, bucket)
        target[key] = int(target.get(key, 0)) + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": not self.errors,
            "source_tenant_id": self.source_tenant_id,
            "target_tenant_id": self.target_tenant_id,
            "dry_run": self.dry_run,
            "bundle_code": self.bundle_code,
            "bundle_version": self.bundle_version,
            "created": self.created,
            "skipped": self.skipped,
            "would_create": self.would_create,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_tenant_id(value: Any, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise BaseCatalogImportError(f"{label} e obrigatorio.")
    return normalized


def _table_exists(db: Session, table_name: str) -> bool:
    return inspect(db.connection()).has_table(table_name)


def _columns(db: Session, table_name: str) -> set[str]:
    if not _table_exists(db, table_name):
        return set()
    return {
        column["name"] for column in inspect(db.connection()).get_columns(table_name)
    }


def _tenant_exists(db: Session, tenant_id: str) -> bool:
    if not _table_exists(db, "tenants"):
        return True
    return bool(
        db.execute(
            text("SELECT 1 FROM tenants WHERE CAST(id AS TEXT) = :tenant_id LIMIT 1"),
            {"tenant_id": tenant_id},
        ).scalar()
    )


def _validate_tenants(
    db: Session, source_tenant_id: str, target_tenant_id: str
) -> None:
    if source_tenant_id == target_tenant_id:
        raise BaseCatalogImportError("Tenant fonte e destino nao podem ser iguais.")
    if not _tenant_exists(db, source_tenant_id):
        raise BaseCatalogImportError(
            f"Tenant fonte nao encontrado: {source_tenant_id}."
        )
    if not _tenant_exists(db, target_tenant_id):
        raise BaseCatalogImportError(
            f"Tenant destino nao encontrado: {target_tenant_id}."
        )


def _template_code(item_type: str, source_id: int) -> str:
    return f"{item_type}:{int(source_id)}"


def _select_rows(db: Session, table_name: str, tenant_id: str) -> list[dict[str, Any]]:
    if not _table_exists(db, table_name):
        return []
    sync_rls_tenant(db, tenant_id)
    order_clause = "ORDER BY id" if "id" in _columns(db, table_name) else ""
    rows = db.execute(
        text(
            f"SELECT * FROM {table_name} WHERE CAST(tenant_id AS TEXT) = :tenant_id {order_clause}"
        ),
        {"tenant_id": tenant_id},
    ).mappings()
    return [dict(row) for row in rows]


def _get_mapping(
    db: Session,
    *,
    tenant_id: str,
    bundle_code: str,
    bundle_version: str,
    item_type: str,
    source_id: int,
    target_table: str,
) -> int | None:
    if not _table_exists(db, "tenant_template_item_installs"):
        return None
    sync_rls_tenant(db, tenant_id)
    return db.execute(
        text(
            """
            SELECT target_id
            FROM tenant_template_item_installs
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
              AND bundle_code = :bundle_code
              AND bundle_version = :bundle_version
              AND item_type = :item_type
              AND template_code = :template_code
              AND target_table = :target_table
              AND status = 'active'
            LIMIT 1
            """
        ),
        {
            "tenant_id": tenant_id,
            "bundle_code": bundle_code,
            "bundle_version": bundle_version,
            "item_type": item_type,
            "template_code": _template_code(item_type, source_id),
            "target_table": target_table,
        },
    ).scalar()


def _record_mapping(
    db: Session,
    *,
    tenant_id: str,
    user_id: int,
    bundle_code: str,
    bundle_version: str,
    item_type: str,
    source_id: int,
    target_table: str,
    target_id: int,
) -> None:
    if not _table_exists(db, "tenant_template_item_installs"):
        return
    existing = _get_mapping(
        db,
        tenant_id=tenant_id,
        bundle_code=bundle_code,
        bundle_version=bundle_version,
        item_type=item_type,
        source_id=source_id,
        target_table=target_table,
    )
    if existing:
        return
    now = _now()
    sync_rls_tenant(db, tenant_id)
    db.execute(
        text(
            """
            INSERT INTO tenant_template_item_installs (
                tenant_id, bundle_code, bundle_version, item_type, template_code,
                target_table, target_id, status, created_by_user_id, created_at, updated_at
            ) VALUES (
                :tenant_id, :bundle_code, :bundle_version, :item_type, :template_code,
                :target_table, :target_id, 'active', :user_id, :now, :now
            )
            """
        ),
        {
            "tenant_id": tenant_id,
            "bundle_code": bundle_code,
            "bundle_version": bundle_version,
            "item_type": item_type,
            "template_code": _template_code(item_type, source_id),
            "target_table": target_table,
            "target_id": int(target_id),
            "user_id": int(user_id),
            "now": now,
        },
    )


def _record_install(db: Session, user_id: int, result: BaseCatalogImportResult) -> None:
    if result.dry_run or not _table_exists(db, "tenant_template_installs"):
        return
    summary = json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True)
    sync_rls_tenant(db, result.target_tenant_id)
    existing_id = db.execute(
        text(
            """
            SELECT id
            FROM tenant_template_installs
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
              AND bundle_code = :bundle_code
              AND bundle_version = :bundle_version
            LIMIT 1
            """
        ),
        {
            "tenant_id": result.target_tenant_id,
            "bundle_code": result.bundle_code,
            "bundle_version": result.bundle_version,
        },
    ).scalar()
    now = _now()
    if existing_id:
        db.execute(
            text(
                """
                UPDATE tenant_template_installs
                   SET status = 'completed',
                       dry_run = :dry_run,
                       created_by_user_id = :user_id,
                       summary = :summary,
                       updated_at = :now
                 WHERE id = :id
                """
            ),
            {
                "id": existing_id,
                "dry_run": False,
                "user_id": int(user_id),
                "summary": summary,
                "now": now,
            },
        )
        return

    db.execute(
        text(
            """
            INSERT INTO tenant_template_installs (
                tenant_id, bundle_code, bundle_version, status, dry_run,
                created_by_user_id, summary, created_at, updated_at
            ) VALUES (
                :tenant_id, :bundle_code, :bundle_version, 'completed', :dry_run,
                :user_id, :summary, :now, :now
            )
            """
        ),
        {
            "tenant_id": result.target_tenant_id,
            "bundle_code": result.bundle_code,
            "bundle_version": result.bundle_version,
            "dry_run": False,
            "user_id": int(user_id),
            "summary": summary,
            "now": now,
        },
    )


def _insert_and_lookup(
    db: Session,
    *,
    table_name: str,
    values: dict[str, Any],
    lookup_sql: str,
    lookup_params: dict[str, Any],
) -> int:
    table_columns = _columns(db, table_name)
    filtered = {
        key: value
        for key, value in values.items()
        if key in table_columns and key != "id"
    }
    if "created_at" in table_columns and "created_at" not in filtered:
        filtered["created_at"] = _now()
    if "updated_at" in table_columns and "updated_at" not in filtered:
        filtered["updated_at"] = _now()
    tenant_id = filtered.get("tenant_id") or lookup_params.get("tenant_id")
    if tenant_id:
        sync_rls_tenant(db, tenant_id)
    column_sql = ", ".join(filtered)
    param_sql = ", ".join(f":{key}" for key in filtered)
    db.execute(
        text(f"INSERT INTO {table_name} ({column_sql}) VALUES ({param_sql})"), filtered
    )
    created_id = db.execute(text(lookup_sql), lookup_params).scalar()
    if not created_id:
        raise BaseCatalogImportError(
            f"Nao foi possivel localizar registro criado em {table_name}."
        )
    return int(created_id)


def _existing_id_by_name(
    db: Session, table_name: str, tenant_id: str, name: str
) -> int | None:
    sync_rls_tenant(db, tenant_id)
    return db.execute(
        text(
            f"""
            SELECT id
            FROM {table_name}
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
              AND lower(trim(nome)) = lower(trim(:nome))
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "nome": name},
    ).scalar()
