from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.base_catalog_import_core import (
    BaseCatalogImportError,
    BaseCatalogImportResult,
    ImageCopier,
    _get_mapping,
    _insert_and_lookup,
    _record_mapping,
    _select_rows,
    sync_rls_tenant,
)


@dataclass(frozen=True)
class S3ImageCopyContext:
    base_url: str
    bucket: str
    client: Any
    extra_args: dict[str, Any]


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


def _build_s3_copy_extra_args(settings: Any) -> dict[str, Any]:
    extra_args: dict[str, Any] = {
        "ContentType": "image/webp",
        "CacheControl": "public, max-age=31536000, immutable",
        "MetadataDirective": "REPLACE",
    }
    expected_owner = str(
        getattr(settings, "PRODUCT_IMAGE_S3_EXPECTED_BUCKET_OWNER", "") or ""
    ).strip()
    if expected_owner:
        extra_args["ExpectedBucketOwner"] = expected_owner
        extra_args["ExpectedSourceBucketOwner"] = expected_owner
    return extra_args


def _build_s3_image_copy_context(public_url: str) -> S3ImageCopyContext | None:
    from app.config import settings
    from app.services.product_image_storage import (
        get_product_image_storage_backend,
        is_s3_product_image_url,
    )

    if get_product_image_storage_backend() != "s3" or not is_s3_product_image_url(
        public_url
    ):
        return None

    base_url = str(settings.PRODUCT_IMAGE_S3_PUBLIC_BASE_URL or "").strip().rstrip("/")
    bucket = str(settings.PRODUCT_IMAGE_S3_BUCKET or "").strip()
    if not base_url or not bucket:
        return None

    import boto3
    from botocore.client import Config as BotoConfig

    client = boto3.client(
        "s3",
        region_name=str(settings.PRODUCT_IMAGE_S3_REGION or "").strip() or None,
        endpoint_url=str(settings.PRODUCT_IMAGE_S3_ENDPOINT_URL or "").strip() or None,
        aws_access_key_id=str(settings.PRODUCT_IMAGE_S3_ACCESS_KEY_ID or "").strip()
        or None,
        aws_secret_access_key=str(
            settings.PRODUCT_IMAGE_S3_SECRET_ACCESS_KEY or ""
        ).strip()
        or None,
        config=BotoConfig(
            signature_version="s3v4",
            s3={
                "addressing_style": (
                    "path" if bool(settings.PRODUCT_IMAGE_S3_USE_PATH_STYLE) else "auto"
                ),
            },
        ),
    )
    return S3ImageCopyContext(
        base_url=base_url,
        bucket=bucket,
        client=client,
        extra_args=_build_s3_copy_extra_args(settings),
    )


def _s3_key_from_public_url(base_url: str, public_url: str) -> str:
    return str(public_url)[len(base_url) + 1 :]


def _copy_s3_product_image_object(
    context: S3ImageCopyContext,
    *,
    source_url: str,
    destination_url: str,
) -> None:
    context.client.copy(
        {
            "Bucket": context.bucket,
            "Key": _s3_key_from_public_url(context.base_url, source_url),
        },
        context.bucket,
        _s3_key_from_public_url(context.base_url, destination_url),
        ExtraArgs=context.extra_args,
    )


def _copy_s3_product_image_variants(
    context: S3ImageCopyContext,
    *,
    public_url: str,
    rewritten_url: str,
) -> None:
    from app.services.product_image_storage import build_product_thumbnail_url

    url_pairs = (
        (public_url, rewritten_url),
        (
            build_product_thumbnail_url(public_url),
            build_product_thumbnail_url(rewritten_url),
        ),
    )
    for source_url, destination_url in url_pairs:
        if source_url and destination_url:
            _copy_s3_product_image_object(
                context,
                source_url=source_url,
                destination_url=destination_url,
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
        context = _build_s3_image_copy_context(public_url)
        if context:
            _copy_s3_product_image_variants(
                context, public_url=public_url, rewritten_url=rewritten
            )
    except Exception as exc:
        raise BaseCatalogImportError(
            f"Falha ao copiar imagem de produto: {exc}"
        ) from exc

    return rewritten


def _find_existing_product_image_id(
    db: Session,
    *,
    tenant_id: str,
    produto_id: int,
    url: str,
) -> int | None:
    sync_rls_tenant(db, tenant_id)
    return db.execute(
        text(
            """
            SELECT id FROM produto_imagens
            WHERE CAST(tenant_id AS TEXT)=:tenant_id
              AND produto_id=:produto_id
              AND url=:url
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "produto_id": produto_id, "url": url},
    ).scalar()


def _create_product_image(
    db: Session,
    *,
    row: dict[str, Any],
    target_tenant_id: str,
    target_product_id: int,
    url: str,
) -> int:
    values = dict(row)
    values.update(
        {"tenant_id": target_tenant_id, "produto_id": target_product_id, "url": url}
    )
    return _insert_and_lookup(
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
        lookup_params={
            "tenant_id": target_tenant_id,
            "produto_id": target_product_id,
            "url": url,
        },
    )


def _is_main_source_image(
    row: dict[str, Any], source_products: dict[int, dict[str, Any]]
) -> bool:
    source_product = source_products.get(int(row["produto_id"])) or {}
    return bool(
        row.get("e_principal")
        or row.get("url") == source_product.get("imagem_principal")
    )


def _count_copyable_product_images(
    rows: list[dict[str, Any]],
    *,
    source_products: dict[int, dict[str, Any]],
    result: BaseCatalogImportResult,
) -> None:
    for row in rows:
        if int(row["produto_id"]) in source_products:
            result.bump("would_create", "produto_imagens")


def _copy_product_image_row(
    db: Session,
    *,
    row: dict[str, Any],
    source_tenant_id: str,
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogImportResult,
    product_map: dict[int, int],
    source_products: dict[int, dict[str, Any]],
    image_copier: ImageCopier,
) -> tuple[int, str] | None:
    source_id = int(row["id"])
    source_product_id = int(row["produto_id"])
    target_product_id = product_map.get(source_product_id)
    if not target_product_id:
        return None

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
        return None

    new_url = image_copier(
        row["url"],
        source_tenant_id=source_tenant_id,
        source_product_id=source_product_id,
        target_tenant_id=target_tenant_id,
        target_product_id=target_product_id,
    )
    existing_id = _find_existing_product_image_id(
        db,
        tenant_id=target_tenant_id,
        produto_id=target_product_id,
        url=new_url,
    )
    target_id = existing_id or _create_product_image(
        db,
        row=row,
        target_tenant_id=target_tenant_id,
        target_product_id=target_product_id,
        url=new_url,
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
        target_id=int(target_id),
    )
    result.bump("skipped" if existing_id else "created", "produto_imagens")
    return (
        (target_product_id, new_url)
        if _is_main_source_image(row, source_products)
        else None
    )


def _update_main_product_images(
    db: Session,
    main_urls_by_target_product: dict[int, str],
    *,
    target_tenant_id: str,
) -> None:
    sync_rls_tenant(db, target_tenant_id)
    for target_product_id, new_url in main_urls_by_target_product.items():
        db.execute(
            text(
                """
                UPDATE produtos
                   SET imagem_principal=:url
                 WHERE id=:id
                   AND CAST(tenant_id AS TEXT)=:tenant_id
                """
            ),
            {
                "id": target_product_id,
                "url": new_url,
                "tenant_id": target_tenant_id,
            },
        )


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
        _count_copyable_product_images(
            rows, source_products=source_products, result=result
        )
        return

    main_urls_by_target_product: dict[int, str] = {}
    for row in rows:
        main_image = _copy_product_image_row(
            db,
            row=row,
            source_tenant_id=source_tenant_id,
            target_tenant_id=target_tenant_id,
            user_id=user_id,
            result=result,
            product_map=product_map,
            source_products=source_products,
            image_copier=image_copier,
        )
        if main_image:
            target_product_id, new_url = main_image
            main_urls_by_target_product[target_product_id] = new_url

    _update_main_product_images(
        db,
        main_urls_by_target_product,
        target_tenant_id=target_tenant_id,
    )
