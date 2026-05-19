from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


DEFAULT_BASE_CATALOG_SOURCE_EMAIL = "admin@mlprohub.com.br"
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
    return datetime.utcnow()


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
    return {column["name"] for column in inspect(db.connection()).get_columns(table_name)}


def _tenant_exists(db: Session, tenant_id: str) -> bool:
    if not _table_exists(db, "tenants"):
        return True
    return bool(
        db.execute(
            text("SELECT 1 FROM tenants WHERE CAST(id AS TEXT) = :tenant_id LIMIT 1"),
            {"tenant_id": tenant_id},
        ).scalar()
    )


def _validate_tenants(db: Session, source_tenant_id: str, target_tenant_id: str) -> None:
    if source_tenant_id == target_tenant_id:
        raise BaseCatalogImportError("Tenant fonte e destino nao podem ser iguais.")
    if not _tenant_exists(db, source_tenant_id):
        raise BaseCatalogImportError(f"Tenant fonte nao encontrado: {source_tenant_id}.")
    if not _tenant_exists(db, target_tenant_id):
        raise BaseCatalogImportError(f"Tenant destino nao encontrado: {target_tenant_id}.")


def _template_code(item_type: str, source_id: int) -> str:
    return f"{item_type}:{int(source_id)}"


def _select_rows(db: Session, table_name: str, tenant_id: str) -> list[dict[str, Any]]:
    if not _table_exists(db, table_name):
        return []
    order_clause = "ORDER BY id" if "id" in _columns(db, table_name) else ""
    rows = db.execute(
        text(f"SELECT * FROM {table_name} WHERE CAST(tenant_id AS TEXT) = :tenant_id {order_clause}"),
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
    filtered = {key: value for key, value in values.items() if key in table_columns and key != "id"}
    if "created_at" in table_columns and "created_at" not in filtered:
        filtered["created_at"] = _now()
    if "updated_at" in table_columns and "updated_at" not in filtered:
        filtered["updated_at"] = _now()
    column_sql = ", ".join(filtered)
    param_sql = ", ".join(f":{key}" for key in filtered)
    db.execute(text(f"INSERT INTO {table_name} ({column_sql}) VALUES ({param_sql})"), filtered)
    created_id = db.execute(text(lookup_sql), lookup_params).scalar()
    if not created_id:
        raise BaseCatalogImportError(f"Nao foi possivel localizar registro criado em {table_name}.")
    return int(created_id)


def _existing_id_by_name(db: Session, table_name: str, tenant_id: str, name: str) -> int | None:
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


def _copy_departments(
    db: Session,
    *,
    source_tenant_id: str,
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogImportResult,
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for row in _select_rows(db, "departamentos", source_tenant_id):
        source_id = int(row["id"])
        mapped_id = _get_mapping(
            db,
            tenant_id=target_tenant_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type="departamento",
            source_id=source_id,
            target_table="departamentos",
        )
        if mapped_id:
            mapping[source_id] = int(mapped_id)
            result.bump("skipped", "departamentos")
            continue
        existing_id = _existing_id_by_name(db, "departamentos", target_tenant_id, row["nome"])
        if existing_id:
            mapping[source_id] = int(existing_id)
            if not result.dry_run:
                _record_mapping(
                    db,
                    tenant_id=target_tenant_id,
                    user_id=user_id,
                    bundle_code=result.bundle_code,
                    bundle_version=result.bundle_version,
                    item_type="departamento",
                    source_id=source_id,
                    target_table="departamentos",
                    target_id=int(existing_id),
                )
            result.bump("skipped", "departamentos")
            continue
        if result.dry_run:
            result.bump("would_create", "departamentos")
            continue
        values = dict(row)
        values.update({"tenant_id": target_tenant_id, "user_id": user_id})
        created_id = _insert_and_lookup(
            db,
            table_name="departamentos",
            values=values,
            lookup_sql="""
                SELECT id FROM departamentos
                WHERE CAST(tenant_id AS TEXT)=:tenant_id AND lower(trim(nome))=lower(trim(:nome))
                LIMIT 1
            """,
            lookup_params={"tenant_id": target_tenant_id, "nome": row["nome"]},
        )
        mapping[source_id] = created_id
        _record_mapping(
            db,
            tenant_id=target_tenant_id,
            user_id=user_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type="departamento",
            source_id=source_id,
            target_table="departamentos",
            target_id=created_id,
        )
        result.bump("created", "departamentos")
    return mapping


def _copy_categories(
    db: Session,
    *,
    source_tenant_id: str,
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogImportResult,
    department_map: dict[int, int],
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    rows = _select_rows(db, "categorias", source_tenant_id)
    for row in rows:
        source_id = int(row["id"])
        mapped_id = _get_mapping(
            db,
            tenant_id=target_tenant_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type="categoria",
            source_id=source_id,
            target_table="categorias",
        )
        if mapped_id:
            mapping[source_id] = int(mapped_id)
            result.bump("skipped", "categorias")
            continue
        target_department_id = department_map.get(int(row["departamento_id"])) if row.get("departamento_id") else None
        existing_id = db.execute(
            text(
                """
                SELECT id
                FROM categorias
                WHERE CAST(tenant_id AS TEXT)=:tenant_id
                  AND lower(trim(nome))=lower(trim(:nome))
                  AND (:departamento_id IS NULL OR departamento_id = :departamento_id)
                LIMIT 1
                """
            ),
            {"tenant_id": target_tenant_id, "nome": row["nome"], "departamento_id": target_department_id},
        ).scalar()
        if existing_id:
            mapping[source_id] = int(existing_id)
            if not result.dry_run:
                _record_mapping(
                    db,
                    tenant_id=target_tenant_id,
                    user_id=user_id,
                    bundle_code=result.bundle_code,
                    bundle_version=result.bundle_version,
                    item_type="categoria",
                    source_id=source_id,
                    target_table="categorias",
                    target_id=int(existing_id),
                )
            result.bump("skipped", "categorias")
            continue
        if result.dry_run:
            result.bump("would_create", "categorias")
            continue
        values = dict(row)
        values.update(
            {
                "tenant_id": target_tenant_id,
                "user_id": user_id,
                "departamento_id": target_department_id,
                "categoria_pai_id": None,
            }
        )
        created_id = _insert_and_lookup(
            db,
            table_name="categorias",
            values=values,
            lookup_sql="""
                SELECT id FROM categorias
                WHERE CAST(tenant_id AS TEXT)=:tenant_id
                  AND lower(trim(nome))=lower(trim(:nome))
                  AND (:departamento_id IS NULL OR departamento_id = :departamento_id)
                LIMIT 1
            """,
            lookup_params={"tenant_id": target_tenant_id, "nome": row["nome"], "departamento_id": target_department_id},
        )
        mapping[source_id] = created_id
        _record_mapping(
            db,
            tenant_id=target_tenant_id,
            user_id=user_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type="categoria",
            source_id=source_id,
            target_table="categorias",
            target_id=created_id,
        )
        result.bump("created", "categorias")

    if not result.dry_run:
        for row in rows:
            source_parent_id = row.get("categoria_pai_id")
            if not source_parent_id:
                continue
            target_id = mapping.get(int(row["id"]))
            target_parent_id = mapping.get(int(source_parent_id))
            if target_id and target_parent_id:
                db.execute(
                    text("UPDATE categorias SET categoria_pai_id=:parent_id WHERE id=:id"),
                    {"id": target_id, "parent_id": target_parent_id},
                )
    return mapping


def _copy_brands(
    db: Session,
    *,
    source_tenant_id: str,
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogImportResult,
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for row in _select_rows(db, "marcas", source_tenant_id):
        source_id = int(row["id"])
        mapped_id = _get_mapping(
            db,
            tenant_id=target_tenant_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type="marca",
            source_id=source_id,
            target_table="marcas",
        )
        if mapped_id:
            mapping[source_id] = int(mapped_id)
            result.bump("skipped", "marcas")
            continue
        existing_id = _existing_id_by_name(db, "marcas", target_tenant_id, row["nome"])
        if existing_id:
            mapping[source_id] = int(existing_id)
            if not result.dry_run:
                _record_mapping(
                    db,
                    tenant_id=target_tenant_id,
                    user_id=user_id,
                    bundle_code=result.bundle_code,
                    bundle_version=result.bundle_version,
                    item_type="marca",
                    source_id=source_id,
                    target_table="marcas",
                    target_id=int(existing_id),
                )
            result.bump("skipped", "marcas")
            continue
        if result.dry_run:
            result.bump("would_create", "marcas")
            continue
        values = dict(row)
        values.update({"tenant_id": target_tenant_id, "user_id": user_id})
        created_id = _insert_and_lookup(
            db,
            table_name="marcas",
            values=values,
            lookup_sql="""
                SELECT id FROM marcas
                WHERE CAST(tenant_id AS TEXT)=:tenant_id AND lower(trim(nome))=lower(trim(:nome))
                LIMIT 1
            """,
            lookup_params={"tenant_id": target_tenant_id, "nome": row["nome"]},
        )
        mapping[source_id] = created_id
        _record_mapping(
            db,
            tenant_id=target_tenant_id,
            user_id=user_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type="marca",
            source_id=source_id,
            target_table="marcas",
            target_id=created_id,
        )
        result.bump("created", "marcas")
    return mapping


def _copy_option_table(
    db: Session,
    *,
    table_name: str,
    item_type: str,
    source_tenant_id: str,
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogImportResult,
) -> dict[int, int]:
    mapping: dict[int, int] = {}
    if not _table_exists(db, table_name):
        return mapping
    for row in _select_rows(db, table_name, source_tenant_id):
        source_id = int(row["id"])
        mapped_id = _get_mapping(
            db,
            tenant_id=target_tenant_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type=item_type,
            source_id=source_id,
            target_table=table_name,
        )
        if mapped_id:
            mapping[source_id] = int(mapped_id)
            result.bump("skipped", table_name)
            continue

        if table_name == "apresentacoes_peso":
            existing_id = db.execute(
                text(
                    """
                    SELECT id FROM apresentacoes_peso
                    WHERE CAST(tenant_id AS TEXT)=:tenant_id AND peso_kg = :peso_kg
                    LIMIT 1
                    """
                ),
                {"tenant_id": target_tenant_id, "peso_kg": row["peso_kg"]},
            ).scalar()
            lookup_sql = """
                SELECT id FROM apresentacoes_peso
                WHERE CAST(tenant_id AS TEXT)=:tenant_id AND peso_kg = :peso_kg
                LIMIT 1
            """
            lookup_params = {"tenant_id": target_tenant_id, "peso_kg": row["peso_kg"]}
        else:
            existing_id = _existing_id_by_name(db, table_name, target_tenant_id, row["nome"])
            lookup_sql = f"""
                SELECT id FROM {table_name}
                WHERE CAST(tenant_id AS TEXT)=:tenant_id AND lower(trim(nome))=lower(trim(:nome))
                LIMIT 1
            """
            lookup_params = {"tenant_id": target_tenant_id, "nome": row["nome"]}

        if existing_id:
            mapping[source_id] = int(existing_id)
            if not result.dry_run:
                _record_mapping(
                    db,
                    tenant_id=target_tenant_id,
                    user_id=user_id,
                    bundle_code=result.bundle_code,
                    bundle_version=result.bundle_version,
                    item_type=item_type,
                    source_id=source_id,
                    target_table=table_name,
                    target_id=int(existing_id),
                )
            result.bump("skipped", table_name)
            continue
        if result.dry_run:
            result.bump("would_create", table_name)
            continue

        values = dict(row)
        values["tenant_id"] = target_tenant_id
        created_id = _insert_and_lookup(
            db,
            table_name=table_name,
            values=values,
            lookup_sql=lookup_sql,
            lookup_params=lookup_params,
        )
        mapping[source_id] = created_id
        _record_mapping(
            db,
            tenant_id=target_tenant_id,
            user_id=user_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type=item_type,
            source_id=source_id,
            target_table=table_name,
            target_id=created_id,
        )
        result.bump("created", table_name)
    return mapping


def _sanitize_product_values(
    row: dict[str, Any],
    *,
    target_tenant_id: str,
    user_id: int,
    department_map: dict[int, int],
    category_map: dict[int, int],
    brand_map: dict[int, int],
    option_maps: dict[str, dict[int, int]],
) -> dict[str, Any]:
    values = dict(row)
    values["tenant_id"] = target_tenant_id
    values["user_id"] = user_id
    values["categoria_id"] = category_map.get(int(row["categoria_id"])) if row.get("categoria_id") else None
    values["departamento_id"] = department_map.get(int(row["departamento_id"])) if row.get("departamento_id") else None
    values["marca_id"] = brand_map.get(int(row["marca_id"])) if row.get("marca_id") else None
    values["produto_pai_id"] = None
    values["produto_predecessor_id"] = None
    values["imagem_principal"] = None

    option_field_map = {
        "linha_racao_id": "linha_racao",
        "porte_animal_id": "porte_animal",
        "fase_publico_id": "fase_publico",
        "tipo_tratamento_id": "tipo_tratamento",
        "sabor_proteina_id": "sabor_proteina",
        "apresentacao_peso_id": "apresentacao_peso",
    }
    for field_name, item_type in option_field_map.items():
        source_value = row.get(field_name)
        values[field_name] = option_maps.get(item_type, {}).get(int(source_value)) if source_value else None

    for field_name in PRODUCT_OPERATIONAL_ZERO_FIELDS:
        values[field_name] = 0
    for field_name in PRODUCT_OPERATIONAL_NULL_FIELDS:
        values[field_name] = None
    values["promocao_ativa"] = False
    values["controle_lote"] = False
    values["crossdocking_dias"] = 0
    return values


def _copy_products(
    db: Session,
    *,
    source_tenant_id: str,
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogImportResult,
    department_map: dict[int, int],
    category_map: dict[int, int],
    brand_map: dict[int, int],
    option_maps: dict[str, dict[int, int]],
) -> tuple[dict[int, int], dict[int, dict[str, Any]]]:
    mapping: dict[int, int] = {}
    source_rows = _select_rows(db, "produtos", source_tenant_id)
    source_by_id = {int(row["id"]): row for row in source_rows}
    for row in source_rows:
        source_id = int(row["id"])
        mapped_id = _get_mapping(
            db,
            tenant_id=target_tenant_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type="produto",
            source_id=source_id,
            target_table="produtos",
        )
        if mapped_id:
            mapping[source_id] = int(mapped_id)
            result.bump("skipped", "produtos")
            continue
        existing_id = db.execute(
            text(
                """
                SELECT id FROM produtos
                WHERE CAST(tenant_id AS TEXT)=:tenant_id
                  AND lower(trim(codigo))=lower(trim(:codigo))
                LIMIT 1
                """
            ),
            {"tenant_id": target_tenant_id, "codigo": row["codigo"]},
        ).scalar()
        if existing_id:
            mapping[source_id] = int(existing_id)
            if not result.dry_run:
                _record_mapping(
                    db,
                    tenant_id=target_tenant_id,
                    user_id=user_id,
                    bundle_code=result.bundle_code,
                    bundle_version=result.bundle_version,
                    item_type="produto",
                    source_id=source_id,
                    target_table="produtos",
                    target_id=int(existing_id),
                )
            result.bump("skipped", "produtos")
            continue
        if result.dry_run:
            result.bump("would_create", "produtos")
            continue
        values = _sanitize_product_values(
            row,
            target_tenant_id=target_tenant_id,
            user_id=user_id,
            department_map=department_map,
            category_map=category_map,
            brand_map=brand_map,
            option_maps=option_maps,
        )
        created_id = _insert_and_lookup(
            db,
            table_name="produtos",
            values=values,
            lookup_sql="""
                SELECT id FROM produtos
                WHERE CAST(tenant_id AS TEXT)=:tenant_id
                  AND lower(trim(codigo))=lower(trim(:codigo))
                LIMIT 1
            """,
            lookup_params={"tenant_id": target_tenant_id, "codigo": row["codigo"]},
        )
        mapping[source_id] = created_id
        _record_mapping(
            db,
            tenant_id=target_tenant_id,
            user_id=user_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type="produto",
            source_id=source_id,
            target_table="produtos",
            target_id=created_id,
        )
        result.bump("created", "produtos")

    if not result.dry_run:
        for source_id, row in source_by_id.items():
            target_id = mapping.get(source_id)
            if not target_id:
                continue
            parent_target_id = mapping.get(int(row["produto_pai_id"])) if row.get("produto_pai_id") else None
            predecessor_target_id = (
                mapping.get(int(row["produto_predecessor_id"])) if row.get("produto_predecessor_id") else None
            )
            if parent_target_id or predecessor_target_id:
                db.execute(
                    text(
                        """
                        UPDATE produtos
                           SET produto_pai_id = :produto_pai_id,
                               produto_predecessor_id = :produto_predecessor_id
                         WHERE id = :id
                        """
                    ),
                    {
                        "id": target_id,
                        "produto_pai_id": parent_target_id,
                        "produto_predecessor_id": predecessor_target_id,
                    },
                )
    return mapping, source_by_id


def rewrite_product_image_url(
    public_url: str,
    *,
    source_tenant_id: str,
    source_product_id: int,
    target_tenant_id: str,
    target_product_id: int,
) -> str:
    return (
        str(public_url)
        .replace(str(source_tenant_id), str(target_tenant_id))
        .replace(f"/{int(source_product_id)}/", f"/{int(target_product_id)}/")
    )


def copy_product_image_url(
    public_url: str,
    *,
    source_tenant_id: str,
    source_product_id: int,
    target_tenant_id: str,
    target_product_id: int,
) -> str:
    rewritten = rewrite_product_image_url(
        public_url,
        source_tenant_id=source_tenant_id,
        source_product_id=source_product_id,
        target_tenant_id=target_tenant_id,
        target_product_id=target_product_id,
    )
    if rewritten == public_url:
        return rewritten

    try:
        from app.config import settings
        from app.services.product_image_storage import (
            build_product_thumbnail_url,
            get_product_image_storage_backend,
            is_s3_product_image_url,
        )

        if get_product_image_storage_backend() == "s3" and is_s3_product_image_url(public_url):
            import boto3
            from botocore.client import Config as BotoConfig

            base_url = str(settings.PRODUCT_IMAGE_S3_PUBLIC_BASE_URL or "").strip().rstrip("/")
            bucket = str(settings.PRODUCT_IMAGE_S3_BUCKET or "").strip()
            if not base_url or not bucket:
                return rewritten

            client = boto3.client(
                "s3",
                region_name=str(settings.PRODUCT_IMAGE_S3_REGION or "").strip() or None,
                endpoint_url=str(settings.PRODUCT_IMAGE_S3_ENDPOINT_URL or "").strip() or None,
                aws_access_key_id=str(settings.PRODUCT_IMAGE_S3_ACCESS_KEY_ID or "").strip() or None,
                aws_secret_access_key=str(settings.PRODUCT_IMAGE_S3_SECRET_ACCESS_KEY or "").strip() or None,
                config=BotoConfig(
                    signature_version="s3v4",
                    s3={
                        "addressing_style": (
                            "path" if bool(settings.PRODUCT_IMAGE_S3_USE_PATH_STYLE) else "auto"
                        ),
                    },
                ),
            )
            for source_url, destination_url in (
                (public_url, rewritten),
                (build_product_thumbnail_url(public_url), build_product_thumbnail_url(rewritten)),
            ):
                if not source_url or not destination_url:
                    continue
                source_key = str(source_url)[len(base_url) + 1 :]
                destination_key = str(destination_url)[len(base_url) + 1 :]
                client.copy_object(
                    Bucket=bucket,
                    CopySource={"Bucket": bucket, "Key": source_key},
                    Key=destination_key,
                    ContentType="image/webp",
                    CacheControl="public, max-age=31536000, immutable",
                    MetadataDirective="REPLACE",
                )
    except Exception as exc:
        raise BaseCatalogImportError(f"Falha ao copiar imagem de produto: {exc}") from exc

    return rewritten


def _copy_product_images(
    db: Session,
    *,
    source_tenant_id: str,
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogImportResult,
    product_map: dict[int, int],
    source_products: dict[int, dict[str, Any]],
    image_copier: ImageCopier,
) -> None:
    rows = _select_rows(db, "produto_imagens", source_tenant_id)
    if result.dry_run:
        for row in rows:
            if int(row["produto_id"]) in source_products:
                result.bump("would_create", "produto_imagens")
        return

    main_urls_by_target_product: dict[int, str] = {}
    for row in rows:
        source_id = int(row["id"])
        source_product_id = int(row["produto_id"])
        target_product_id = product_map.get(source_product_id)
        if not target_product_id:
            continue
        mapped_id = _get_mapping(
            db,
            tenant_id=target_tenant_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type="produto_imagem",
            source_id=source_id,
            target_table="produto_imagens",
        )
        if mapped_id:
            result.bump("skipped", "produto_imagens")
            continue
        new_url = image_copier(
            row["url"],
            source_tenant_id=source_tenant_id,
            source_product_id=source_product_id,
            target_tenant_id=target_tenant_id,
            target_product_id=target_product_id,
        )
        existing_id = db.execute(
            text(
                """
                SELECT id FROM produto_imagens
                WHERE CAST(tenant_id AS TEXT)=:tenant_id
                  AND produto_id=:produto_id
                  AND url=:url
                LIMIT 1
                """
            ),
            {"tenant_id": target_tenant_id, "produto_id": target_product_id, "url": new_url},
        ).scalar()
        if existing_id:
            _record_mapping(
                db,
                tenant_id=target_tenant_id,
                user_id=user_id,
                bundle_code=result.bundle_code,
                bundle_version=result.bundle_version,
                item_type="produto_imagem",
                source_id=source_id,
                target_table="produto_imagens",
                target_id=int(existing_id),
            )
            result.bump("skipped", "produto_imagens")
        else:
            values = dict(row)
            values.update({"tenant_id": target_tenant_id, "produto_id": target_product_id, "url": new_url})
            created_id = _insert_and_lookup(
                db,
                table_name="produto_imagens",
                values=values,
                lookup_sql="""
                    SELECT id FROM produto_imagens
                    WHERE CAST(tenant_id AS TEXT)=:tenant_id
                      AND produto_id=:produto_id
                      AND url=:url
                    LIMIT 1
                """,
                lookup_params={"tenant_id": target_tenant_id, "produto_id": target_product_id, "url": new_url},
            )
            _record_mapping(
                db,
                tenant_id=target_tenant_id,
                user_id=user_id,
                bundle_code=result.bundle_code,
                bundle_version=result.bundle_version,
                item_type="produto_imagem",
                source_id=source_id,
                target_table="produto_imagens",
                target_id=created_id,
            )
            result.bump("created", "produto_imagens")
        source_product = source_products.get(source_product_id) or {}
        if row.get("e_principal") or row.get("url") == source_product.get("imagem_principal"):
            main_urls_by_target_product[target_product_id] = new_url

    for target_product_id, new_url in main_urls_by_target_product.items():
        db.execute(
            text("UPDATE produtos SET imagem_principal=:url WHERE id=:id"),
            {"id": target_product_id, "url": new_url},
        )


def _copy_product_relations(
    db: Session,
    *,
    source_tenant_id: str,
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogImportResult,
    product_map: dict[int, int],
) -> None:
    if _table_exists(db, "produto_kit_componentes"):
        for row in _select_rows(db, "produto_kit_componentes", source_tenant_id):
            source_kit_id = int(row["kit_id"])
            source_component_id = int(row["produto_componente_id"])
            target_kit_id = product_map.get(source_kit_id)
            target_component_id = product_map.get(source_component_id)
            if not target_kit_id or not target_component_id:
                continue
            if result.dry_run:
                result.bump("would_create", "produto_kit_componentes")
                continue
            existing = db.execute(
                text(
                    """
                    SELECT id FROM produto_kit_componentes
                    WHERE CAST(tenant_id AS TEXT)=:tenant_id
                      AND kit_id=:kit_id
                      AND produto_componente_id=:produto_componente_id
                    LIMIT 1
                    """
                ),
                {
                    "tenant_id": target_tenant_id,
                    "kit_id": target_kit_id,
                    "produto_componente_id": target_component_id,
                },
            ).scalar()
            if existing:
                result.bump("skipped", "produto_kit_componentes")
                continue
            values = dict(row)
            values.update(
                {
                    "tenant_id": target_tenant_id,
                    "kit_id": target_kit_id,
                    "produto_componente_id": target_component_id,
                }
            )
            _insert_and_lookup(
                db,
                table_name="produto_kit_componentes",
                values=values,
                lookup_sql="""
                    SELECT id FROM produto_kit_componentes
                    WHERE CAST(tenant_id AS TEXT)=:tenant_id
                      AND kit_id=:kit_id
                      AND produto_componente_id=:produto_componente_id
                    LIMIT 1
                """,
                lookup_params={
                    "tenant_id": target_tenant_id,
                    "kit_id": target_kit_id,
                    "produto_componente_id": target_component_id,
                },
            )
            result.bump("created", "produto_kit_componentes")

    if _table_exists(db, "produto_granel_vinculos"):
        for row in _select_rows(db, "produto_granel_vinculos", source_tenant_id):
            source_origin_id = int(row["produto_origem_id"])
            source_bulk_id = int(row["produto_granel_id"])
            target_origin_id = product_map.get(source_origin_id)
            target_bulk_id = product_map.get(source_bulk_id)
            if not target_origin_id or not target_bulk_id:
                continue
            if result.dry_run:
                result.bump("would_create", "produto_granel_vinculos")
                continue
            existing = db.execute(
                text(
                    """
                    SELECT id FROM produto_granel_vinculos
                    WHERE CAST(tenant_id AS TEXT)=:tenant_id
                      AND produto_origem_id=:produto_origem_id
                      AND produto_granel_id=:produto_granel_id
                    LIMIT 1
                    """
                ),
                {
                    "tenant_id": target_tenant_id,
                    "produto_origem_id": target_origin_id,
                    "produto_granel_id": target_bulk_id,
                },
            ).scalar()
            if existing:
                result.bump("skipped", "produto_granel_vinculos")
                continue
            values = dict(row)
            values.update(
                {
                    "tenant_id": target_tenant_id,
                    "produto_origem_id": target_origin_id,
                    "produto_granel_id": target_bulk_id,
                    "user_id": user_id,
                }
            )
            _insert_and_lookup(
                db,
                table_name="produto_granel_vinculos",
                values=values,
                lookup_sql="""
                    SELECT id FROM produto_granel_vinculos
                    WHERE CAST(tenant_id AS TEXT)=:tenant_id
                      AND produto_origem_id=:produto_origem_id
                      AND produto_granel_id=:produto_granel_id
                    LIMIT 1
                """,
                lookup_params={
                    "tenant_id": target_tenant_id,
                    "produto_origem_id": target_origin_id,
                    "produto_granel_id": target_bulk_id,
                },
            )
            result.bump("created", "produto_granel_vinculos")


def import_base_catalog(
    *,
    db: Session,
    source_tenant_id: Any,
    target_tenant_id: Any,
    user_id: int,
    dry_run: bool = True,
    bundle_code: str = DEFAULT_BASE_CATALOG_BUNDLE_CODE,
    bundle_version: str = DEFAULT_BASE_CATALOG_BUNDLE_VERSION,
    image_copier: ImageCopier | None = None,
) -> dict[str, Any]:
    source_tenant = _normalize_tenant_id(source_tenant_id, "source_tenant_id")
    target_tenant = _normalize_tenant_id(target_tenant_id, "target_tenant_id")
    _validate_tenants(db, source_tenant, target_tenant)

    result = BaseCatalogImportResult(
        source_tenant_id=source_tenant,
        target_tenant_id=target_tenant,
        dry_run=bool(dry_run),
        bundle_code=bundle_code,
        bundle_version=bundle_version,
    )
    if not _table_exists(db, "tenant_template_item_installs"):
        result.warnings.append("Tabela tenant_template_item_installs ausente; idempotencia limitada.")

    try:
        department_map = _copy_departments(
            db,
            source_tenant_id=source_tenant,
            target_tenant_id=target_tenant,
            user_id=int(user_id),
            result=result,
        )
        category_map = _copy_categories(
            db,
            source_tenant_id=source_tenant,
            target_tenant_id=target_tenant,
            user_id=int(user_id),
            result=result,
            department_map=department_map,
        )
        brand_map = _copy_brands(
            db,
            source_tenant_id=source_tenant,
            target_tenant_id=target_tenant,
            user_id=int(user_id),
            result=result,
        )
        option_maps: dict[str, dict[int, int]] = {}
        for table_name, item_type in SUPPORT_OPTION_TABLES:
            option_maps[item_type] = _copy_option_table(
                db,
                table_name=table_name,
                item_type=item_type,
                source_tenant_id=source_tenant,
                target_tenant_id=target_tenant,
                user_id=int(user_id),
                result=result,
            )

        product_map, source_products = _copy_products(
            db,
            source_tenant_id=source_tenant,
            target_tenant_id=target_tenant,
            user_id=int(user_id),
            result=result,
            department_map=department_map,
            category_map=category_map,
            brand_map=brand_map,
            option_maps=option_maps,
        )
        _copy_product_relations(
            db,
            source_tenant_id=source_tenant,
            target_tenant_id=target_tenant,
            user_id=int(user_id),
            result=result,
            product_map=product_map,
        )
        _copy_product_images(
            db,
            source_tenant_id=source_tenant,
            target_tenant_id=target_tenant,
            user_id=int(user_id),
            result=result,
            product_map=product_map,
            source_products=source_products,
            image_copier=image_copier or copy_product_image_url,
        )
        _record_install(db, int(user_id), result)
        return result.to_dict()
    except SQLAlchemyError as exc:
        raise BaseCatalogImportError(f"Falha ao importar catalogo base: {exc}") from exc
