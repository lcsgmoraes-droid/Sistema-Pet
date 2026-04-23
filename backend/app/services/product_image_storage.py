from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Optional
from urllib.parse import urlparse
import shutil
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings


WEBP_CONTENT_TYPE = "image/webp"


@dataclass(frozen=True)
class PreparedProductImage:
    original_bytes: bytes
    thumbnail_bytes: bytes
    width: int
    height: int
    original_size_bytes: int
    content_type: str = WEBP_CONTENT_TYPE
    extension: str = "webp"


@dataclass(frozen=True)
class StoredProductImage:
    url: str
    thumbnail_url: str
    image_token: str


def get_product_image_storage_backend() -> str:
    backend = str(settings.PRODUCT_IMAGE_STORAGE_BACKEND or "local").strip().lower()
    return backend if backend in {"local", "s3"} else "local"


def _local_base_dir() -> Path:
    return Path(settings.PRODUCT_IMAGE_LOCAL_BASE_DIR)


def _local_public_prefix() -> str:
    raw_path = str(settings.PRODUCT_IMAGE_LOCAL_BASE_DIR or "").replace("\\", "/").strip()
    segments = [segment for segment in raw_path.split("/") if segment not in {"", "."}]
    if not segments:
        return "/uploads/produtos"
    if "uploads" in segments:
        start = segments.index("uploads")
        return f"/{'/'.join(segments[start:])}"
    return f"/uploads/{'/'.join(segments)}"


def _s3_prefix() -> str:
    return str(settings.PRODUCT_IMAGE_S3_PREFIX or "").strip().strip("/")


def _compose_s3_key(relative_key: str) -> str:
    prefix = _s3_prefix()
    clean_relative_key = str(relative_key).strip().lstrip("/")
    if not prefix:
        return clean_relative_key
    return f"{prefix}/{clean_relative_key}"


def _build_s3_public_url(storage_key: str) -> str:
    base_url = str(settings.PRODUCT_IMAGE_S3_PUBLIC_BASE_URL or "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError(
            "PRODUCT_IMAGE_S3_PUBLIC_BASE_URL precisa estar configurada para servir imagens externas.",
        )
    return f"{base_url}/{storage_key.lstrip('/')}"


def _get_s3_client():
    bucket = str(settings.PRODUCT_IMAGE_S3_BUCKET or "").strip()
    if not bucket:
        raise RuntimeError("PRODUCT_IMAGE_S3_BUCKET não configurado.")

    import boto3
    from botocore.client import Config as BotoConfig

    client_config = BotoConfig(
        signature_version="s3v4",
        s3={
            "addressing_style": (
                "path" if bool(settings.PRODUCT_IMAGE_S3_USE_PATH_STYLE) else "auto"
            ),
        },
    )

    return boto3.client(
        "s3",
        region_name=str(settings.PRODUCT_IMAGE_S3_REGION or "").strip() or None,
        endpoint_url=str(settings.PRODUCT_IMAGE_S3_ENDPOINT_URL or "").strip() or None,
        aws_access_key_id=str(settings.PRODUCT_IMAGE_S3_ACCESS_KEY_ID or "").strip() or None,
        aws_secret_access_key=str(settings.PRODUCT_IMAGE_S3_SECRET_ACCESS_KEY or "").strip() or None,
        config=client_config,
    )


def build_product_image_relative_keys(
    tenant_id: str | int,
    produto_id: int,
    image_token: Optional[str] = None,
) -> tuple[str, str, str]:
    token = (image_token or uuid.uuid4().hex).replace(".", "_")
    base = PurePosixPath(str(tenant_id), str(produto_id))
    original_relative_key = str(base / "originais" / f"{token}.webp")
    thumbnail_relative_key = str(base / "thumbs" / f"{token}.webp")
    return token, original_relative_key, thumbnail_relative_key


def build_product_thumbnail_url(public_url: Optional[str]) -> Optional[str]:
    if not public_url:
        return None

    normalized = str(public_url).strip()
    if "/originais/" in normalized:
        return normalized.replace("/originais/", "/thumbs/")
    return normalized


def get_product_image_dimensions(image: Image.Image) -> tuple[int, int]:
    return int(image.width or 0), int(image.height or 0)


def prepare_product_image_variants(
    file_bytes: bytes,
    *,
    max_dimension: Optional[int] = None,
    thumbnail_size: Optional[int] = None,
    webp_quality: Optional[int] = None,
) -> PreparedProductImage:
    max_dimension = int(max_dimension or settings.PRODUCT_IMAGE_MAX_DIMENSION or 1600)
    thumbnail_size = int(
        thumbnail_size or settings.PRODUCT_IMAGE_THUMBNAIL_SIZE or 420,
    )
    webp_quality = int(webp_quality or settings.PRODUCT_IMAGE_WEBP_QUALITY or 82)

    try:
        with Image.open(BytesIO(file_bytes)) as source_image:
            image = ImageOps.exif_transpose(source_image)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

            original_image = image.copy()
            original_image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            original_width, original_height = get_product_image_dimensions(original_image)

            original_buffer = BytesIO()
            original_image.save(
                original_buffer,
                format="WEBP",
                quality=webp_quality,
                method=6,
            )
            original_bytes = original_buffer.getvalue()

            thumbnail_image = image.copy()
            thumbnail_image.thumbnail((thumbnail_size, thumbnail_size), Image.Resampling.LANCZOS)
            thumbnail_buffer = BytesIO()
            thumbnail_image.save(
                thumbnail_buffer,
                format="WEBP",
                quality=max(min(webp_quality - 8, 80), 60),
                method=6,
            )
            thumbnail_bytes = thumbnail_buffer.getvalue()
    except UnidentifiedImageError as exc:
        raise ValueError("Arquivo enviado não é uma imagem válida.") from exc

    return PreparedProductImage(
        original_bytes=original_bytes,
        thumbnail_bytes=thumbnail_bytes,
        width=original_width,
        height=original_height,
        original_size_bytes=len(original_bytes),
    )


def _write_local_bytes(relative_key: str, content: bytes) -> str:
    target_path = _local_base_dir() / Path(relative_key)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(content)
    return f"{_local_public_prefix()}/{relative_key}".replace("\\", "/")


def _store_local_product_image(
    original_relative_key: str,
    thumbnail_relative_key: str,
    prepared_image: PreparedProductImage,
) -> StoredProductImage:
    original_url = _write_local_bytes(original_relative_key, prepared_image.original_bytes)
    thumbnail_url = _write_local_bytes(
        thumbnail_relative_key,
        prepared_image.thumbnail_bytes,
    )
    image_token = Path(original_relative_key).stem
    return StoredProductImage(
        url=original_url,
        thumbnail_url=thumbnail_url,
        image_token=image_token,
    )


def _store_s3_product_image(
    original_relative_key: str,
    thumbnail_relative_key: str,
    prepared_image: PreparedProductImage,
) -> StoredProductImage:
    client = _get_s3_client()
    bucket = str(settings.PRODUCT_IMAGE_S3_BUCKET or "").strip()
    original_key = _compose_s3_key(original_relative_key)
    thumbnail_key = _compose_s3_key(thumbnail_relative_key)

    put_kwargs = {
        "ContentType": prepared_image.content_type,
        "CacheControl": "public, max-age=31536000, immutable",
    }
    if bool(settings.PRODUCT_IMAGE_S3_PUBLIC_READ):
        put_kwargs["ACL"] = "public-read"

    client.put_object(
        Bucket=bucket,
        Key=original_key,
        Body=prepared_image.original_bytes,
        **put_kwargs,
    )
    client.put_object(
        Bucket=bucket,
        Key=thumbnail_key,
        Body=prepared_image.thumbnail_bytes,
        **put_kwargs,
    )

    return StoredProductImage(
        url=_build_s3_public_url(original_key),
        thumbnail_url=_build_s3_public_url(thumbnail_key),
        image_token=Path(original_relative_key).stem,
    )


def save_product_image_variants(
    tenant_id: str | int,
    produto_id: int,
    prepared_image: PreparedProductImage,
    *,
    image_token: Optional[str] = None,
) -> StoredProductImage:
    _, original_relative_key, thumbnail_relative_key = build_product_image_relative_keys(
        tenant_id,
        produto_id,
        image_token=image_token,
    )

    if get_product_image_storage_backend() == "s3":
        return _store_s3_product_image(
            original_relative_key,
            thumbnail_relative_key,
            prepared_image,
        )

    return _store_local_product_image(
        original_relative_key,
        thumbnail_relative_key,
        prepared_image,
    )


def is_local_product_image_url(public_url: Optional[str]) -> bool:
    return bool(public_url and str(public_url).startswith(_local_public_prefix()))


def _s3_public_base_url() -> str:
    return str(settings.PRODUCT_IMAGE_S3_PUBLIC_BASE_URL or "").strip().rstrip("/")


def is_s3_product_image_url(public_url: Optional[str]) -> bool:
    if not public_url:
        return False
    base_url = _s3_public_base_url()
    return bool(base_url and str(public_url).startswith(f"{base_url}/"))


def _local_public_url_to_path(public_url: str) -> Optional[Path]:
    prefix = _local_public_prefix().rstrip("/")
    if not public_url.startswith(f"{prefix}/"):
        return None
    relative_key = public_url[len(prefix) + 1 :]
    return _local_base_dir() / Path(relative_key)


def read_local_product_image_bytes(public_url: str) -> bytes:
    file_path = _local_public_url_to_path(public_url)
    if file_path is None or not file_path.exists():
        raise FileNotFoundError(f"Imagem local não encontrada: {public_url}")
    return file_path.read_bytes()


def _delete_empty_parent_dirs(file_path: Path, stop_path: Path) -> None:
    current = file_path.parent
    stop_path = stop_path.resolve()

    while current.exists():
        try:
            current.resolve().relative_to(stop_path)
        except ValueError:
            break

        if current == stop_path:
            break

        if any(current.iterdir()):
            break

        current.rmdir()
        current = current.parent


def _delete_local_product_image(public_url: str) -> bool:
    file_path = _local_public_url_to_path(public_url)
    if file_path is None or not file_path.exists():
        return False

    file_path.unlink()
    _delete_empty_parent_dirs(file_path, _local_base_dir())
    return True


def _delete_s3_product_image(public_url: str) -> bool:
    base_url = _s3_public_base_url()
    if not base_url or not public_url.startswith(f"{base_url}/"):
        return False

    storage_key = public_url[len(base_url) + 1 :]
    client = _get_s3_client()
    client.delete_object(
        Bucket=str(settings.PRODUCT_IMAGE_S3_BUCKET or "").strip(),
        Key=storage_key,
    )
    return True


def delete_product_image_assets(public_url: Optional[str]) -> None:
    if not public_url:
        return

    urls_to_delete = [str(public_url)]
    thumbnail_url = build_product_thumbnail_url(public_url)
    if thumbnail_url and thumbnail_url not in urls_to_delete:
        urls_to_delete.append(thumbnail_url)

    for target_url in urls_to_delete:
        if is_local_product_image_url(target_url):
            _delete_local_product_image(target_url)
            continue

        if is_s3_product_image_url(target_url):
            _delete_s3_product_image(target_url)


def copy_local_product_image(public_url: str, destination_path: Path) -> None:
    source_path = _local_public_url_to_path(public_url)
    if source_path is None or not source_path.exists():
        raise FileNotFoundError(f"Imagem local não encontrada: {public_url}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)
