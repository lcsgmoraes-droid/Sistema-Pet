"""Copia somente fotos entre produtos com GTIN e identidade compativeis.

O cadastro e os campos comerciais do tenant destino permanecem intactos.
Fontes sao informadas explicitamente e consultadas na ordem recebida.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.services.base_catalog_enrichment_service import (
    _active_rows,
    _unique_rows_by_gtin,
    _update_target_product,
    assess_product_identity_compatibility,
)
from app.services.base_catalog_import_core import _record_mapping, _validate_tenants
from app.services.base_catalog_import_images import (
    _create_product_image,
    copy_product_image_url,
)
from app.services.product_image_storage import (
    get_product_image_storage_backend,
    is_s3_product_image_url,
)

MAX_IMAGES_PER_PRODUCT = 5
IMAGE_ONLY_BUNDLE_CODE = "fotos-produto-gtin"
IMAGE_ONLY_BUNDLE_VERSION = "v1"


@dataclass(frozen=True)
class ImageCandidate:
    gtin: str
    source_tenant_id: str
    source_product_id: int
    target_product_id: int
    score: float
    images: tuple[dict[str, Any], ...]


@dataclass
class ImageCopyResult:
    target_tenant_id: str
    source_tenant_ids: list[str]
    dry_run: bool
    target_unique_gtins: int = 0
    target_ambiguous_gtins: int = 0
    target_invalid_gtins: int = 0
    candidate_products: int = 0
    candidate_images: int = 0
    copied_products: int = 0
    copied_images: int = 0
    skipped: Counter[str] = field(default_factory=Counter)
    sources: Counter[str] = field(default_factory=Counter)
    samples: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "dry_run": self.dry_run,
            "target_tenant_id": self.target_tenant_id,
            "source_tenant_ids": self.source_tenant_ids,
            "target_unique_gtins": self.target_unique_gtins,
            "target_ambiguous_gtins": self.target_ambiguous_gtins,
            "target_invalid_gtins": self.target_invalid_gtins,
            "candidate_products": self.candidate_products,
            "candidate_images": self.candidate_images,
            "copied_products": self.copied_products,
            "copied_images": self.copied_images,
            "skipped": dict(sorted(self.skipped.items())),
            "sources": dict(sorted(self.sources.items())),
            "samples": self.samples,
        }


def _ordered_images(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Seleciona uma principal e ate quatro imagens adicionais do mesmo produto."""
    valid = []
    seen_urls = set()
    for row in rows:
        url = str(row.get("url") or "").strip()
        if not url or url in seen_urls or not is_s3_product_image_url(url):
            continue
        valid.append(row)
        seen_urls.add(url)
    main = next((row for row in valid if row.get("e_principal")), None)
    valid.sort(key=lambda row: (int(row.get("ordem") or 0), int(row["id"])))
    if main is None and valid:
        main = valid[0]
    if main is None:
        return ()
    ordered = [main, *(row for row in valid if row["id"] != main["id"])]
    return tuple(ordered[:MAX_IMAGES_PER_PRODUCT])


def copy_missing_images_by_gtin(
    *,
    db: Session,
    source_tenant_ids: list[str],
    target_tenant_id: str,
    user_id: int,
    dry_run: bool = True,
) -> dict[str, Any]:
    if not source_tenant_ids or len(source_tenant_ids) != len(set(source_tenant_ids)):
        raise ValueError("Informe fontes distintas, em ordem de preferencia.")
    if get_product_image_storage_backend() != "s3":
        raise ValueError("Este fluxo exige imagens no armazenamento S3 configurado.")
    for source_tenant_id in source_tenant_ids:
        _validate_tenants(db, source_tenant_id, target_tenant_id)

    result = ImageCopyResult(target_tenant_id, source_tenant_ids, dry_run)
    targets = [
        row
        for row in _active_rows(db, "produtos", target_tenant_id)
        if row.get("ativo") is not False and row.get("situacao") is not False
    ]
    target_unique, result.target_ambiguous_gtins, result.target_invalid_gtins = (
        _unique_rows_by_gtin(targets)
    )
    result.target_unique_gtins = len(target_unique)
    target_images = defaultdict(list)
    for row in _active_rows(db, "produto_imagens", target_tenant_id):
        target_images[int(row["produto_id"])].append(row)

    candidates: dict[str, ImageCandidate] = {}
    for source_tenant_id in source_tenant_ids:
        sources = [
            row
            for row in _active_rows(db, "produtos", source_tenant_id)
            if row.get("ativo") is not False and row.get("situacao") is not False
        ]
        source_unique, ambiguous, invalid = _unique_rows_by_gtin(sources)
        result.skipped[f"source_ambiguous:{source_tenant_id}"] = ambiguous
        result.skipped[f"source_invalid:{source_tenant_id}"] = invalid
        source_images = defaultdict(list)
        for row in _active_rows(db, "produto_imagens", source_tenant_id):
            source_images[int(row["produto_id"])].append(row)

        for gtin in sorted(set(source_unique) & set(target_unique)):
            if gtin in candidates:
                continue
            source = source_unique[gtin]
            target = target_unique[gtin]
            target_id = int(target["id"])
            if str(target.get("imagem_principal") or "").strip() or target_images.get(
                target_id
            ):
                result.skipped["target_has_image"] += 1
                continue
            identity = assess_product_identity_compatibility(source, target)
            if not identity.compatible:
                result.skipped["identity_incompatible"] += 1
                continue
            images = _ordered_images(source_images.get(int(source["id"]), []))
            if not images:
                result.skipped["source_without_s3_image"] += 1
                continue
            candidates[gtin] = ImageCandidate(
                gtin=gtin,
                source_tenant_id=source_tenant_id,
                source_product_id=int(source["id"]),
                target_product_id=target_id,
                score=identity.score,
                images=images,
            )

    result.candidate_products = len(candidates)
    result.candidate_images = sum(len(item.images) for item in candidates.values())
    for item in candidates.values():
        result.sources[item.source_tenant_id] += 1
        if len(result.samples) < 20:
            result.samples.append(
                {
                    "gtin": item.gtin,
                    "source_tenant_id": item.source_tenant_id,
                    "source_product_id": item.source_product_id,
                    "target_product_id": item.target_product_id,
                    "image_count": len(item.images),
                    "identity_score": item.score,
                }
            )
        if dry_run:
            continue
        main_url = None
        for order, source_image in enumerate(item.images):
            source_url = str(source_image["url"])
            new_url = copy_product_image_url(
                source_url,
                source_tenant_id=item.source_tenant_id,
                source_product_id=item.source_product_id,
                target_tenant_id=target_tenant_id,
                target_product_id=item.target_product_id,
            )
            if new_url == source_url:
                raise ValueError("URL da imagem fonte nao identifica o tenant/produto.")
            image_row = dict(source_image, ordem=order, e_principal=order == 0)
            target_image_id = _create_product_image(
                db,
                row=image_row,
                target_tenant_id=target_tenant_id,
                target_product_id=item.target_product_id,
                url=new_url,
            )
            _record_mapping(
                db,
                tenant_id=target_tenant_id,
                user_id=user_id,
                bundle_code=IMAGE_ONLY_BUNDLE_CODE,
                bundle_version=IMAGE_ONLY_BUNDLE_VERSION,
                item_type="produto_imagem_gtin",
                source_id=int(source_image["id"]),
                target_table="produto_imagens",
                target_id=target_image_id,
            )
            main_url = main_url or new_url
            result.copied_images += 1
        _update_target_product(
            db,
            target_tenant_id=target_tenant_id,
            target_product_id=item.target_product_id,
            updates={"imagem_principal": main_url},
        )
        result.copied_products += 1
    return result.to_dict()
