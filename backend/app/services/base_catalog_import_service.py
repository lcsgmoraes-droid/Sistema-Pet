from __future__ import annotations

from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.services.base_catalog_import_catalog import (
    _copy_brands,
    _copy_categories,
    _copy_departments,
    _copy_option_table,
    _copy_products,
    _create_category,
    _create_product,
    _existing_id_by_name,
    _find_existing_category_id,
    _find_existing_product_id,
    _link_category_parents,
    _link_product_hierarchy,
    _record_or_skip_mapped_item,
    _sanitize_product_values,
)
from app.services.base_catalog_import_core import (
    DEFAULT_BASE_CATALOG_BUNDLE_CODE,
    DEFAULT_BASE_CATALOG_BUNDLE_VERSION,
    DEFAULT_BASE_CATALOG_SOURCE_EMAIL,
    PRODUCT_OPERATIONAL_NULL_FIELDS,
    PRODUCT_OPERATIONAL_ZERO_FIELDS,
    SUPPORT_OPTION_TABLES,
    BaseCatalogImportError,
    BaseCatalogImportResult,
    ImageCopier,
    _columns,
    _get_mapping,
    _insert_and_lookup,
    _normalize_tenant_id,
    _now,
    _record_install,
    _record_mapping,
    _select_rows,
    _table_exists,
    _template_code,
    _tenant_exists,
    _validate_tenants,
    sync_rls_tenant,
)
from app.services.base_catalog_import_images import (
    S3ImageCopyContext,
    _build_s3_copy_extra_args,
    _build_s3_image_copy_context,
    _copy_product_image_row,
    _copy_product_images,
    _copy_s3_product_image_object,
    _copy_s3_product_image_variants,
    _count_copyable_product_images,
    _create_product_image,
    _find_existing_product_image_id,
    _is_main_source_image,
    _s3_key_from_public_url,
    _update_main_product_images,
    copy_product_image_url,
    rewrite_product_image_url,
)
from app.services.base_catalog_import_relations import (
    _copy_bulk_link_row,
    _copy_bulk_links,
    _copy_kit_component_row,
    _copy_kit_components,
    _copy_product_relations,
    _relation_exists,
)


_COMPAT_PRIVATE_REEXPORTS = (
    DEFAULT_BASE_CATALOG_SOURCE_EMAIL,
    PRODUCT_OPERATIONAL_NULL_FIELDS,
    PRODUCT_OPERATIONAL_ZERO_FIELDS,
    S3ImageCopyContext,
    SUPPORT_OPTION_TABLES,
    _build_s3_copy_extra_args,
    _build_s3_image_copy_context,
    _columns,
    _copy_brands,
    _copy_bulk_link_row,
    _copy_bulk_links,
    _copy_categories,
    _copy_departments,
    _copy_kit_component_row,
    _copy_kit_components,
    _copy_option_table,
    _copy_product_image_row,
    _copy_product_images,
    _copy_product_relations,
    _copy_products,
    _copy_s3_product_image_object,
    _copy_s3_product_image_variants,
    _count_copyable_product_images,
    _create_category,
    _create_product,
    _create_product_image,
    _existing_id_by_name,
    _find_existing_category_id,
    _find_existing_product_id,
    _find_existing_product_image_id,
    _get_mapping,
    _insert_and_lookup,
    _is_main_source_image,
    _link_category_parents,
    _link_product_hierarchy,
    _normalize_tenant_id,
    _now,
    _record_install,
    _record_mapping,
    _record_or_skip_mapped_item,
    _relation_exists,
    _s3_key_from_public_url,
    _sanitize_product_values,
    _select_rows,
    _table_exists,
    _template_code,
    _tenant_exists,
    _update_main_product_images,
    _validate_tenants,
    sync_rls_tenant,
    rewrite_product_image_url,
)


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
        result.warnings.append(
            "Tabela tenant_template_item_installs ausente; idempotencia limitada."
        )

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
