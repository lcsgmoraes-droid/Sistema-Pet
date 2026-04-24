from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

import requests
from sqlalchemy.orm import Session

from app.produtos_models import Produto, ProdutoImagem
from app.services.product_image_storage import (
    prepare_product_image_variants,
    save_product_image_variants,
)


_IMAGE_HINTS = (
    "imagem",
    "image",
    "images",
    "foto",
    "fotos",
    "photo",
    "photos",
    "thumb",
    "thumbnail",
    "midia",
    "media",
    "anexo",
    "attachment",
    "gallery",
    "galeria",
    "cover",
    "capa",
)
_IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".tiff",
    ".svg",
    ".avif",
)
_REMOTE_IMAGE_TIMEOUT_SECONDS = 30


def _normalize_remote_image_url(value: Optional[str]) -> Optional[str]:
    raw = str(value or "").strip()
    if not raw:
        return None

    if raw.startswith("//"):
        raw = f"https:{raw}"

    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return raw


def _score_image_candidate(url: str, path: tuple[str, ...]) -> int:
    normalized_path = [segment.strip().lower() for segment in path if str(segment or "").strip()]
    path_text = " ".join(normalized_path)
    parsed = urlparse(url)
    url_path = (parsed.path or "").lower()
    url_query = (parsed.query or "").lower()

    score = 0

    if any(hint in segment for segment in normalized_path for hint in _IMAGE_HINTS):
        score += 100

    if any(url_path.endswith(extension) for extension in _IMAGE_EXTENSIONS):
        score += 35
    elif any(marker in url_path for marker in ("/image", "/images/", "/imagem", "/media/", "/thumb")):
        score += 18

    if any(marker in url_query for marker in ("image", "imagem", "img", "thumb", "photo", "foto")):
        score += 8

    if "produto" in path_text or "product" in path_text:
        score += 4

    return score


def _collect_image_candidates(node, path: tuple[str, ...], collected: list[tuple[int, str]]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _collect_image_candidates(value, (*path, str(key)), collected)
        return

    if isinstance(node, (list, tuple, set)):
        for index, value in enumerate(node):
            _collect_image_candidates(value, (*path, f"[{index}]"), collected)
        return

    if not isinstance(node, str):
        return

    normalized_url = _normalize_remote_image_url(node)
    if not normalized_url:
        return

    score = _score_image_candidate(normalized_url, path)
    if score >= 30:
        collected.append((score, normalized_url))


def extract_bling_product_image_url(payload: Optional[dict]) -> Optional[str]:
    candidates: list[tuple[int, str]] = []
    _collect_image_candidates(payload or {}, tuple(), candidates)

    if not candidates:
        return None

    unique_by_url: dict[str, int] = {}
    for score, url in candidates:
        unique_by_url[url] = max(score, unique_by_url.get(url, 0))

    ordered = sorted(
        unique_by_url.items(),
        key=lambda item: (-item[1], len(item[0])),
    )
    return ordered[0][0] if ordered else None


def product_has_any_image(produto: Produto) -> bool:
    if str(getattr(produto, "imagem_principal", "") or "").strip():
        return True

    imagens = getattr(produto, "imagens", []) or []
    return any(str(getattr(imagem, "url", "") or "").strip() for imagem in imagens)


def _download_remote_image_bytes(image_url: str) -> bytes:
    response = requests.get(
        image_url,
        timeout=_REMOTE_IMAGE_TIMEOUT_SECONDS,
        headers={"User-Agent": "SistemaPet/bling-image-import"},
    )
    response.raise_for_status()

    file_bytes = response.content or b""
    if not file_bytes:
        raise ValueError("A imagem retornada pelo Bling veio vazia.")

    return file_bytes


def attach_remote_image_to_product(
    db: Session,
    *,
    tenant_id: str | int,
    produto: Produto,
    image_url: str,
    force_primary: bool = False,
) -> ProdutoImagem:
    file_bytes = _download_remote_image_bytes(image_url)
    prepared_image = prepare_product_image_variants(file_bytes)
    stored_image = save_product_image_variants(
        tenant_id=tenant_id,
        produto_id=produto.id,
        prepared_image=prepared_image,
    )

    existing_images = list(getattr(produto, "imagens", []) or [])
    if force_primary:
        for existing_image in existing_images:
            existing_image.e_principal = False

    has_primary = any(bool(getattr(existing_image, "e_principal", False)) for existing_image in existing_images)
    has_main_url = bool(str(getattr(produto, "imagem_principal", "") or "").strip())
    should_be_primary = force_primary or (not has_primary and not has_main_url)
    next_order = max((int(getattr(existing_image, "ordem", 0) or 0) for existing_image in existing_images), default=0) + 1

    new_image = ProdutoImagem(
        tenant_id=tenant_id,
        produto_id=produto.id,
        url=stored_image.url,
        ordem=next_order,
        e_principal=should_be_primary,
        tamanho=prepared_image.original_size_bytes,
        largura=prepared_image.width,
        altura=prepared_image.height,
    )
    db.add(new_image)

    if should_be_primary or not has_main_url:
        produto.imagem_principal = new_image.url

    return new_image
