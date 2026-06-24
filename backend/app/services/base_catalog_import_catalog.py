from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.base_catalog_import_core import (
    BaseCatalogImportResult,
    PRODUCT_OPERATIONAL_NULL_FIELDS,
    PRODUCT_OPERATIONAL_ZERO_FIELDS,
    _existing_id_by_name,
    _get_mapping,
    _insert_and_lookup,
    _record_mapping,
    _select_rows,
    _table_exists,
    sync_rls_tenant,
)


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
        existing_id = _existing_id_by_name(
            db, "departamentos", target_tenant_id, row["nome"]
        )
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


def _record_or_skip_mapped_item(
    db: Session,
    *,
    mapping: dict[int, int],
    source_id: int,
    target_id: int,
    tenant_id: str,
    user_id: int,
    result: BaseCatalogImportResult,
    item_type: str,
    target_table: str,
    result_key: str,
) -> None:
    mapping[source_id] = int(target_id)
    if not result.dry_run:
        _record_mapping(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type=item_type,
            source_id=source_id,
            target_table=target_table,
            target_id=int(target_id),
        )
    result.bump("skipped", result_key)


def _find_existing_category_id(
    db: Session,
    *,
    tenant_id: str,
    name: str,
    department_id: int | None,
) -> int | None:
    sync_rls_tenant(db, tenant_id)
    return db.execute(
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
        {"tenant_id": tenant_id, "nome": name, "departamento_id": department_id},
    ).scalar()


def _create_category(
    db: Session,
    *,
    row: dict[str, Any],
    target_tenant_id: str,
    user_id: int,
    target_department_id: int | None,
) -> int:
    values = dict(row)
    values.update(
        {
            "tenant_id": target_tenant_id,
            "user_id": user_id,
            "departamento_id": target_department_id,
            "categoria_pai_id": None,
        }
    )
    return _insert_and_lookup(
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
        lookup_params={
            "tenant_id": target_tenant_id,
            "nome": row["nome"],
            "departamento_id": target_department_id,
        },
    )


def _link_category_parents(
    db: Session,
    *,
    rows: list[dict[str, Any]],
    mapping: dict[int, int],
    target_tenant_id: str,
) -> None:
    sync_rls_tenant(db, target_tenant_id)
    for row in rows:
        source_parent_id = row.get("categoria_pai_id")
        if not source_parent_id:
            continue
        target_id = mapping.get(int(row["id"]))
        target_parent_id = mapping.get(int(source_parent_id))
        if target_id and target_parent_id:
            db.execute(
                text(
                    """
                    UPDATE categorias
                       SET categoria_pai_id=:parent_id
                     WHERE id=:id
                       AND CAST(tenant_id AS TEXT)=:tenant_id
                    """
                ),
                {
                    "id": target_id,
                    "parent_id": target_parent_id,
                    "tenant_id": target_tenant_id,
                },
            )


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
        target_department_id = (
            department_map.get(int(row["departamento_id"]))
            if row.get("departamento_id")
            else None
        )
        existing_id = _find_existing_category_id(
            db,
            tenant_id=target_tenant_id,
            name=row["nome"],
            department_id=target_department_id,
        )
        if existing_id:
            _record_or_skip_mapped_item(
                db,
                mapping=mapping,
                source_id=source_id,
                target_id=int(existing_id),
                tenant_id=target_tenant_id,
                user_id=user_id,
                result=result,
                item_type="categoria",
                target_table="categorias",
                result_key="categorias",
            )
            continue
        if result.dry_run:
            result.bump("would_create", "categorias")
            continue
        created_id = _create_category(
            db,
            row=row,
            target_tenant_id=target_tenant_id,
            user_id=user_id,
            target_department_id=target_department_id,
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
        _link_category_parents(
            db,
            rows=rows,
            mapping=mapping,
            target_tenant_id=target_tenant_id,
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
            sync_rls_tenant(db, target_tenant_id)
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
            existing_id = _existing_id_by_name(
                db, table_name, target_tenant_id, row["nome"]
            )
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
    values["categoria_id"] = (
        category_map.get(int(row["categoria_id"])) if row.get("categoria_id") else None
    )
    values["departamento_id"] = (
        department_map.get(int(row["departamento_id"]))
        if row.get("departamento_id")
        else None
    )
    values["marca_id"] = (
        brand_map.get(int(row["marca_id"])) if row.get("marca_id") else None
    )
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
        values[field_name] = (
            option_maps.get(item_type, {}).get(int(source_value))
            if source_value
            else None
        )

    for field_name in PRODUCT_OPERATIONAL_ZERO_FIELDS:
        values[field_name] = 0
    for field_name in PRODUCT_OPERATIONAL_NULL_FIELDS:
        values[field_name] = None
    values["promocao_ativa"] = False
    values["controle_lote"] = False
    values["crossdocking_dias"] = 0
    return values


def _find_existing_product_id(
    db: Session,
    *,
    tenant_id: str,
    codigo: str,
) -> int | None:
    sync_rls_tenant(db, tenant_id)
    return db.execute(
        text(
            """
            SELECT id FROM produtos
            WHERE CAST(tenant_id AS TEXT)=:tenant_id
              AND lower(trim(codigo))=lower(trim(:codigo))
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "codigo": codigo},
    ).scalar()


def _create_product(
    db: Session,
    *,
    row: dict[str, Any],
    target_tenant_id: str,
    user_id: int,
    department_map: dict[int, int],
    category_map: dict[int, int],
    brand_map: dict[int, int],
    option_maps: dict[str, dict[int, int]],
) -> int:
    values = _sanitize_product_values(
        row,
        target_tenant_id=target_tenant_id,
        user_id=user_id,
        department_map=department_map,
        category_map=category_map,
        brand_map=brand_map,
        option_maps=option_maps,
    )
    return _insert_and_lookup(
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


def _link_product_hierarchy(
    db: Session,
    *,
    source_products: dict[int, dict[str, Any]],
    mapping: dict[int, int],
    target_tenant_id: str,
) -> None:
    sync_rls_tenant(db, target_tenant_id)
    for source_id, row in source_products.items():
        target_id = mapping.get(source_id)
        if not target_id:
            continue
        parent_target_id = (
            mapping.get(int(row["produto_pai_id"]))
            if row.get("produto_pai_id")
            else None
        )
        predecessor_target_id = (
            mapping.get(int(row["produto_predecessor_id"]))
            if row.get("produto_predecessor_id")
            else None
        )
        if parent_target_id or predecessor_target_id:
            db.execute(
                text(
                    """
                    UPDATE produtos
                       SET produto_pai_id = :produto_pai_id,
                           produto_predecessor_id = :produto_predecessor_id
                     WHERE id = :id
                       AND CAST(tenant_id AS TEXT) = :tenant_id
                    """
                ),
                {
                    "id": target_id,
                    "tenant_id": target_tenant_id,
                    "produto_pai_id": parent_target_id,
                    "produto_predecessor_id": predecessor_target_id,
                },
            )


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
        existing_id = _find_existing_product_id(
            db, tenant_id=target_tenant_id, codigo=row["codigo"]
        )
        if existing_id:
            _record_or_skip_mapped_item(
                db,
                mapping=mapping,
                source_id=source_id,
                target_id=int(existing_id),
                tenant_id=target_tenant_id,
                user_id=user_id,
                result=result,
                item_type="produto",
                target_table="produtos",
                result_key="produtos",
            )
            continue
        if result.dry_run:
            result.bump("would_create", "produtos")
            continue
        created_id = _create_product(
            db,
            row=row,
            target_tenant_id=target_tenant_id,
            user_id=user_id,
            department_map=department_map,
            category_map=category_map,
            brand_map=brand_map,
            option_maps=option_maps,
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
        _link_product_hierarchy(
            db,
            source_products=source_by_id,
            mapping=mapping,
            target_tenant_id=target_tenant_id,
        )
    return mapping, source_by_id
