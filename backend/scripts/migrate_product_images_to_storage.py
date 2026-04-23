#!/usr/bin/env python
"""Migra imagens de produtos para o pipeline otimizado atual.

Uso comum:
  python backend/scripts/migrate_product_images_to_storage.py --dry-run
  python backend/scripts/migrate_product_images_to_storage.py --tenant-id TENANT
  python backend/scripts/migrate_product_images_to_storage.py --cleanup-local

Com o backend configurado como:
  - local: regrava em /uploads/produtos/<tenant>/<produto>/originais|thumbs
  - s3: envia para o bucket S3-compatível configurado
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

if str(os.environ.get("DEBUG", "")).strip().lower() not in {"", "0", "1", "true", "false"}:
    os.environ["DEBUG"] = "false"

from sqlalchemy.orm import joinedload

from app.config import settings
from app.db import SessionLocal
from app.produtos_models import Produto, ProdutoImagem
from app.services.product_image_storage import (
    build_product_image_relative_keys,
    delete_product_image_assets,
    get_product_image_storage_backend,
    is_local_product_image_url,
    prepare_product_image_variants,
    read_local_product_image_bytes,
    save_product_image_variants,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migra imagens de produtos para WebP otimizado + thumbnail.",
    )
    parser.add_argument("--tenant-id", help="Filtra por tenant_id.")
    parser.add_argument("--produto-id", type=int, help="Filtra por produto_id.")
    parser.add_argument("--limit", type=int, help="Limita a quantidade processada.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nao grava nada; apenas valida as imagens e mostra o que seria feito.",
    )
    parser.add_argument(
        "--cleanup-local",
        action="store_true",
        help="Remove o arquivo local legado apos migrar com sucesso.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocessa mesmo URLs ja no padrao /originais/.",
    )
    return parser.parse_args()


def _image_token_from_url(url: str) -> str | None:
    parsed = urlparse(str(url))
    path = parsed.path if parsed.scheme else str(url)
    token = Path(path).stem.strip()
    return token or None


def _already_migrated(url: str) -> bool:
    return "/originais/" in str(url)


def _preview_target(tenant_id: str, produto_id: int, current_url: str) -> str:
    token = _image_token_from_url(current_url)
    _, original_relative_key, _ = build_product_image_relative_keys(
        tenant_id=tenant_id,
        produto_id=produto_id,
        image_token=token,
    )
    backend = get_product_image_storage_backend()
    if backend == "s3":
        base_url = str(settings.PRODUCT_IMAGE_S3_PUBLIC_BASE_URL or "").strip().rstrip("/")
        if base_url:
            prefix = str(settings.PRODUCT_IMAGE_S3_PREFIX or "").strip().strip("/")
            path = f"{prefix}/{original_relative_key}" if prefix else original_relative_key
            return f"{base_url}/{path}".replace("//", "/").replace(":/", "://")
        return f"s3://{settings.PRODUCT_IMAGE_S3_BUCKET}/{original_relative_key}"
    return f"/uploads/produtos/{original_relative_key}"


def _iter_imagens(db, args: argparse.Namespace):
    query = (
        db.query(ProdutoImagem)
        .options(joinedload(ProdutoImagem.produto))
        .order_by(ProdutoImagem.id.asc())
    )
    if args.tenant_id:
        query = query.filter(ProdutoImagem.tenant_id == args.tenant_id)
    if args.produto_id:
        query = query.filter(ProdutoImagem.produto_id == args.produto_id)
    if args.limit:
        query = query.limit(args.limit)
    return query.all()


def migrate_one(db, imagem: ProdutoImagem, args: argparse.Namespace) -> tuple[str, str]:
    current_url = str(imagem.url or "").strip()
    if not current_url:
        return "skipped", f"imagem {imagem.id}: sem URL"

    if _already_migrated(current_url) and not args.force:
        return "skipped", f"imagem {imagem.id}: ja esta no padrao otimizado"

    if not is_local_product_image_url(current_url):
        return "skipped", f"imagem {imagem.id}: origem nao local ({current_url})"

    try:
        source_bytes = read_local_product_image_bytes(current_url)
        prepared = prepare_product_image_variants(source_bytes)
    except FileNotFoundError as exc:
        db.rollback()
        return "failed", f"imagem {imagem.id}: arquivo nao encontrado ({exc})"
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return "failed", f"imagem {imagem.id}: erro ao preparar ({exc})"

    preview_target = _preview_target(str(imagem.tenant_id), int(imagem.produto_id), current_url)
    if args.dry_run:
        return (
            "preview",
            " | ".join(
                [
                    f"imagem {imagem.id}",
                    f"produto {imagem.produto_id}",
                    f"origem={current_url}",
                    f"destino={preview_target}",
                    f"dimensoes={prepared.width}x{prepared.height}",
                    f"tamanho={prepared.original_size_bytes} bytes",
                ],
            ),
        )

    try:
        saved = save_product_image_variants(
            tenant_id=str(imagem.tenant_id),
            produto_id=int(imagem.produto_id),
            prepared_image=prepared,
            image_token=_image_token_from_url(current_url),
        )

        old_url = current_url
        imagem.url = saved.url
        imagem.tamanho = prepared.original_size_bytes
        imagem.largura = prepared.width
        imagem.altura = prepared.height

        produto: Produto | None = imagem.produto
        if produto and (bool(imagem.e_principal) or produto.imagem_principal == old_url):
            produto.imagem_principal = saved.url

        db.commit()

        if args.cleanup_local and old_url != saved.url and is_local_product_image_url(old_url):
            delete_product_image_assets(old_url)

        return (
            "migrated",
            f"imagem {imagem.id}: {old_url} -> {saved.url}",
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return "failed", f"imagem {imagem.id}: erro ao salvar ({exc})"


def main() -> int:
    args = parse_args()
    db = SessionLocal()
    stats = {
        "preview": 0,
        "migrated": 0,
        "skipped": 0,
        "failed": 0,
    }

    print(f"Backend de destino: {get_product_image_storage_backend()}")
    if get_product_image_storage_backend() == "s3":
        print(f"Bucket: {settings.PRODUCT_IMAGE_S3_BUCKET or '(nao configurado)'}")

    try:
        imagens = _iter_imagens(db, args)
        print(f"Imagens selecionadas: {len(imagens)}")

        for imagem in imagens:
            status, message = migrate_one(db, imagem, args)
            stats[status] += 1
            print(f"[{status.upper()}] {message}")

        print("\nResumo:")
        for key in ("preview", "migrated", "skipped", "failed"):
            print(f"  {key}: {stats[key]}")

        return 1 if stats["failed"] else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
