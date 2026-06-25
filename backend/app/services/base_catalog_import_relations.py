from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.base_catalog_import_core import (
    BaseCatalogImportResult,
    _insert_and_lookup,
    _select_rows,
    _table_exists,
    sync_rls_tenant,
)


def _relation_exists(
    db: Session,
    *,
    table_name: str,
    tenant_id: str,
    first_column: str,
    first_id: int,
    second_column: str,
    second_id: int,
) -> bool:
    sync_rls_tenant(db, tenant_id)
    return bool(
        db.execute(
            text(
                f"""
                SELECT id FROM {table_name}
                WHERE CAST(tenant_id AS TEXT)=:tenant_id
                  AND {first_column}=:first_id
                  AND {second_column}=:second_id
                LIMIT 1
                """
            ),
            {
                "tenant_id": tenant_id,
                "first_id": first_id,
                "second_id": second_id,
            },
        ).scalar()
    )


def _copy_kit_component_row(
    db: Session,
    *,
    row: dict[str, Any],
    target_tenant_id: str,
    result: BaseCatalogImportResult,
    product_map: dict[int, int],
) -> None:
    target_kit_id = product_map.get(int(row["kit_id"]))
    target_component_id = product_map.get(int(row["produto_componente_id"]))
    if not target_kit_id or not target_component_id:
        return
    if result.dry_run:
        result.bump("would_create", "produto_kit_componentes")
        return
    if _relation_exists(
        db,
        table_name="produto_kit_componentes",
        tenant_id=target_tenant_id,
        first_column="kit_id",
        first_id=target_kit_id,
        second_column="produto_componente_id",
        second_id=target_component_id,
    ):
        result.bump("skipped", "produto_kit_componentes")
        return

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


def _copy_bulk_link_row(
    db: Session,
    *,
    row: dict[str, Any],
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogImportResult,
    product_map: dict[int, int],
) -> None:
    target_origin_id = product_map.get(int(row["produto_origem_id"]))
    target_bulk_id = product_map.get(int(row["produto_granel_id"]))
    if not target_origin_id or not target_bulk_id:
        return
    if result.dry_run:
        result.bump("would_create", "produto_granel_vinculos")
        return
    if _relation_exists(
        db,
        table_name="produto_granel_vinculos",
        tenant_id=target_tenant_id,
        first_column="produto_origem_id",
        first_id=target_origin_id,
        second_column="produto_granel_id",
        second_id=target_bulk_id,
    ):
        result.bump("skipped", "produto_granel_vinculos")
        return

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


def _copy_kit_components(
    db: Session,
    *,
    source_tenant_id: str,
    target_tenant_id: str,
    result: BaseCatalogImportResult,
    product_map: dict[int, int],
) -> None:
    if not _table_exists(db, "produto_kit_componentes"):
        return
    for row in _select_rows(db, "produto_kit_componentes", source_tenant_id):
        _copy_kit_component_row(
            db,
            row=row,
            target_tenant_id=target_tenant_id,
            result=result,
            product_map=product_map,
        )


def _copy_bulk_links(
    db: Session,
    *,
    source_tenant_id: str,
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogImportResult,
    product_map: dict[int, int],
) -> None:
    if not _table_exists(db, "produto_granel_vinculos"):
        return
    for row in _select_rows(db, "produto_granel_vinculos", source_tenant_id):
        _copy_bulk_link_row(
            db,
            row=row,
            target_tenant_id=target_tenant_id,
            user_id=user_id,
            result=result,
            product_map=product_map,
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
    _copy_kit_components(
        db,
        source_tenant_id=source_tenant_id,
        target_tenant_id=target_tenant_id,
        result=result,
        product_map=product_map,
    )
    _copy_bulk_links(
        db,
        source_tenant_id=source_tenant_id,
        target_tenant_id=target_tenant_id,
        user_id=user_id,
        result=result,
        product_map=product_map,
    )
