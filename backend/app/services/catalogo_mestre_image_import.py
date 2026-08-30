"""Inventario e estagio protegido de imagens nomeadas por GTIN/EAN.

O fluxo nunca cria produtos e nunca publica arquivos. Imagens aplicadas ficam
inativas, com revisao e direitos pendentes, em uma pasta que nao e servida pelo
backend. A ativacao/publicacao deve ser feita por um fluxo de curadoria futuro.
"""

from __future__ import annotations

import csv
import hashlib
import re
import shutil
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import quote

from PIL import Image, UnidentifiedImageError
from sqlalchemy import JSON, bindparam, text

from app.services.catalogo_mestre_core import INITIAL_CATALOG_TYPES, normalize_gtin

SUPPORTED_IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})
SUPPORTED_IMAGE_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
DEFAULT_IMAGE_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_PROTECTED_STAGING_DIR = Path("uploads/catalogo_mestre_pendente")
READY_STATUS = "pronto_para_estagio"

_FILENAME_PATTERN = re.compile(
    r"^(?P<gtin>\d{8,14})_(?P<label>.+)\.(?P<extension>jpe?g|png|webp)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CatalogImageCandidate:
    path: Path
    filename: str
    gtin: str | None
    label: str | None
    status: str
    detail: str | None = None
    sha256: str | None = None
    width: int | None = None
    height: int | None = None
    size_bytes: int | None = None
    image_format: str | None = None
    reported_source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "arquivo": self.filename,
            "gtin": self.gtin,
            "rotulo": self.label,
            "status_leitura": self.status,
            "detalhe_leitura": self.detail,
            "sha256": self.sha256,
            "largura": self.width,
            "altura": self.height,
            "tamanho_bytes": self.size_bytes,
            "formato": self.image_format,
            "fonte_relatorio": self.reported_source,
        }


@dataclass(frozen=True)
class CatalogImagePlanItem:
    candidate: CatalogImageCandidate
    status: str
    detail: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    catalog_type: str | None = None
    order: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = self.candidate.to_dict()
        payload.update(
            {
                "status": self.status,
                "detalhe": self.detail,
                "produto_mestre_id": self.product_id,
                "produto_mestre_nome": self.product_name,
                "tipo_catalogo": self.catalog_type,
                "ordem_candidata": self.order,
            }
        )
        return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_source_manifest(directory: Path) -> dict[str, tuple[str | None, str | None]]:
    manifest_path = directory / "relatorio_download.csv"
    if not manifest_path.is_file():
        return {}

    by_filename: dict[str, tuple[str | None, str | None]] = {}
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            original_path = str(row.get("arquivo") or "").strip()
            filename = re.split(r"[\\/]", original_path)[-1].strip()
            if not filename:
                continue
            reported_gtin = normalize_gtin(row.get("ean"))
            reported_source = str(row.get("fonte") or "").strip() or None
            by_filename[filename.casefold()] = (reported_gtin, reported_source)
    return by_filename


def _read_candidate(
    path: Path,
    max_bytes: int,
    manifest: Mapping[str, tuple[str | None, str | None]],
) -> CatalogImageCandidate:
    filename = path.name
    if path.suffix.casefold() not in SUPPORTED_IMAGE_SUFFIXES:
        return CatalogImageCandidate(
            path=path,
            filename=filename,
            gtin=None,
            label=None,
            status="extensao_nao_suportada",
        )

    match = _FILENAME_PATTERN.fullmatch(filename)
    if not match:
        return CatalogImageCandidate(
            path=path,
            filename=filename,
            gtin=None,
            label=None,
            status="nome_sem_gtin",
            detail="Use o formato EAN_NOME.jpg, .jpeg, .png ou .webp.",
        )

    raw_gtin = match.group("gtin")
    gtin = normalize_gtin(raw_gtin)
    if not gtin:
        return CatalogImageCandidate(
            path=path,
            filename=filename,
            gtin=raw_gtin,
            label=match.group("label").strip(),
            status="gtin_invalido",
        )

    manifest_gtin, reported_source = manifest.get(filename.casefold(), (None, None))
    if manifest_gtin and manifest_gtin != gtin:
        return CatalogImageCandidate(
            path=path,
            filename=filename,
            gtin=gtin,
            label=match.group("label").strip(),
            status="gtin_diverge_do_relatorio",
            detail=f"Relatorio informa {manifest_gtin}; arquivo informa {gtin}.",
            reported_source=reported_source,
        )

    size_bytes = path.stat().st_size
    if size_bytes <= 0 or size_bytes > max_bytes:
        return CatalogImageCandidate(
            path=path,
            filename=filename,
            gtin=gtin,
            label=match.group("label").strip(),
            status="tamanho_invalido",
            detail=f"Arquivo com {size_bytes} bytes; limite: {max_bytes}.",
            size_bytes=size_bytes,
            reported_source=reported_source,
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                image_format = str(image.format or "").upper()
                width, height = image.size
                image.verify()
        if image_format not in SUPPORTED_IMAGE_FORMATS:
            raise ValueError(f"formato real nao suportado: {image_format or 'ausente'}")
        if width <= 0 or height <= 0:
            raise ValueError("dimensoes invalidas")
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        UnidentifiedImageError,
        ValueError,
    ) as exc:
        return CatalogImageCandidate(
            path=path,
            filename=filename,
            gtin=gtin,
            label=match.group("label").strip(),
            status="imagem_invalida",
            detail=str(exc),
            size_bytes=size_bytes,
            reported_source=reported_source,
        )

    return CatalogImageCandidate(
        path=path,
        filename=filename,
        gtin=gtin,
        label=match.group("label").strip(),
        status="valido",
        sha256=_sha256(path),
        width=width,
        height=height,
        size_bytes=size_bytes,
        image_format=image_format,
        reported_source=reported_source,
    )


def discover_image_candidates(
    source_dir: str | Path,
    *,
    max_bytes: int = DEFAULT_IMAGE_MAX_BYTES,
) -> list[CatalogImageCandidate]:
    directory = Path(source_dir).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError(f"Diretorio de imagens nao encontrado: {directory}")
    if max_bytes <= 0:
        raise ValueError("max_bytes deve ser positivo.")
    manifest = _read_source_manifest(directory)
    return [
        _read_candidate(path, max_bytes, manifest)
        for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold())
        if path.is_file() and path.name.casefold() != "relatorio_download.csv"
    ]


def build_image_import_plan(
    candidates: Iterable[CatalogImageCandidate],
    master_rows: Iterable[Mapping[str, Any]],
    image_rows: Iterable[Mapping[str, Any]],
    *,
    image_target: int = 5,
) -> list[CatalogImagePlanItem]:
    if image_target < 1:
        raise ValueError("image_target deve ser maior que zero.")

    masters_by_gtin: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in master_rows:
        gtin = str(row.get("gtin") or "")
        if gtin:
            masters_by_gtin[gtin].append(row)

    images_by_product: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    hash_products: dict[str, set[int]] = defaultdict(set)
    for row in image_rows:
        product_id = int(row["produto_id"])
        images_by_product[product_id].append(row)
        file_hash = str(row.get("hash_arquivo") or "")
        if file_hash:
            hash_products[file_hash].add(product_id)

    occupied_by_product: dict[int, int] = {}
    next_order_by_product: dict[int, int] = {}
    for product_id, rows in images_by_product.items():
        occupied_by_product[product_id] = sum(
            1
            for row in rows
            if bool(row.get("ativo")) or row.get("status_revisao") == "pendente"
        )
        next_order_by_product[product_id] = (
            max((int(row.get("ordem") or 0) for row in rows), default=-1) + 1
        )

    planned_hash_products: dict[str, set[int]] = defaultdict(set)
    plan: list[CatalogImagePlanItem] = []

    for candidate in candidates:
        if candidate.status != "valido":
            plan.append(
                CatalogImagePlanItem(
                    candidate=candidate,
                    status=candidate.status,
                    detail=candidate.detail,
                )
            )
            continue

        matches = masters_by_gtin.get(str(candidate.gtin), [])
        if not matches:
            plan.append(
                CatalogImagePlanItem(
                    candidate=candidate,
                    status="sem_produto_no_mestre",
                    detail="O arquivo nao cria produto automaticamente.",
                )
            )
            continue
        if len(matches) > 1:
            plan.append(
                CatalogImagePlanItem(
                    candidate=candidate,
                    status="gtin_ambiguo_no_mestre",
                    detail=f"GTIN encontrado em {len(matches)} produtos mestres.",
                )
            )
            continue

        master = matches[0]
        product_id = int(master["id"])
        product_name = str(master.get("nome") or "")
        catalog_type = str(master.get("tipo_catalogo") or "")
        common = {
            "product_id": product_id,
            "product_name": product_name,
            "catalog_type": catalog_type,
        }
        if catalog_type not in INITIAL_CATALOG_TYPES:
            plan.append(
                CatalogImagePlanItem(
                    candidate=candidate,
                    status="produto_fora_do_escopo",
                    detail="Tipo do produto mestre nao pertence a fase inicial.",
                    **common,
                )
            )
            continue

        file_hash = str(candidate.sha256)
        existing_hash_products = hash_products.get(file_hash, set())
        planned_hashes = planned_hash_products.get(file_hash, set())
        if product_id in existing_hash_products or product_id in planned_hashes:
            plan.append(
                CatalogImagePlanItem(
                    candidate=candidate,
                    status="imagem_duplicada_no_produto",
                    **common,
                )
            )
            continue
        other_products = (existing_hash_products | planned_hashes) - {product_id}
        if other_products:
            plan.append(
                CatalogImagePlanItem(
                    candidate=candidate,
                    status="hash_vinculado_a_outro_produto",
                    detail="Exige revisao de identidade antes de reutilizar a imagem.",
                    **common,
                )
            )
            continue

        occupied = occupied_by_product.get(product_id, 0)
        product_target = max(
            image_target,
            int(master.get("imagem_meta_quantidade") or image_target),
        )
        if occupied >= product_target:
            plan.append(
                CatalogImagePlanItem(
                    candidate=candidate,
                    status="meta_de_imagens_atingida",
                    detail=f"Produto ja possui {occupied} imagens/candidatas.",
                    **common,
                )
            )
            continue

        order = next_order_by_product.get(product_id, 0)
        plan.append(
            CatalogImagePlanItem(
                candidate=candidate,
                status=READY_STATUS,
                order=order,
                **common,
            )
        )
        occupied_by_product[product_id] = occupied + 1
        next_order_by_product[product_id] = order + 1
        planned_hash_products[file_hash].add(product_id)

    return plan


def _load_master_rows(db, gtins: set[str], *, lock: bool) -> list[Mapping[str, Any]]:
    if not gtins:
        return []
    sql = """
        SELECT id, gtin, nome, tipo_catalogo, imagem_meta_quantidade
          FROM catalogo_mestre_produtos
         WHERE gtin IN :gtins
         ORDER BY gtin, id
    """
    if lock:
        sql += " FOR UPDATE"
    statement = text(sql).bindparams(bindparam("gtins", expanding=True))
    return list(db.execute(statement, {"gtins": sorted(gtins)}).mappings().all())


def _load_image_rows(
    db,
    product_ids: set[int],
    candidate_hashes: set[str],
) -> list[Mapping[str, Any]]:
    if not product_ids and not candidate_hashes:
        return []
    filters: list[str] = []
    params: dict[str, Any] = {}
    if product_ids:
        filters.append("produto_id IN :product_ids")
        params["product_ids"] = sorted(product_ids)
    if candidate_hashes:
        filters.append("hash_arquivo IN :candidate_hashes")
        params["candidate_hashes"] = sorted(candidate_hashes)
    statement = text(
        """
        SELECT produto_id, hash_arquivo, ordem, ativo, status_revisao
          FROM catalogo_mestre_imagens
         WHERE """
        + " OR ".join(filters)
    )
    if product_ids:
        statement = statement.bindparams(bindparam("product_ids", expanding=True))
    if candidate_hashes:
        statement = statement.bindparams(bindparam("candidate_hashes", expanding=True))
    return list(db.execute(statement, params).mappings().all())


def prepare_image_import(
    db,
    source_dir: str | Path,
    *,
    image_target: int = 5,
    max_bytes: int = DEFAULT_IMAGE_MAX_BYTES,
    lock_products: bool = False,
) -> list[CatalogImagePlanItem]:
    candidates = discover_image_candidates(source_dir, max_bytes=max_bytes)
    valid_candidates = [item for item in candidates if item.status == "valido"]
    gtins = {str(item.gtin) for item in valid_candidates if item.gtin}
    hashes = {str(item.sha256) for item in valid_candidates if item.sha256}
    master_rows = _load_master_rows(db, gtins, lock=lock_products)
    product_ids = {int(row["id"]) for row in master_rows}
    image_rows = _load_image_rows(db, product_ids, hashes)
    return build_image_import_plan(
        candidates,
        master_rows,
        image_rows,
        image_target=image_target,
    )


def summarize_image_import_plan(
    plan: Iterable[CatalogImagePlanItem],
    *,
    dry_run: bool,
    staged_images: int = 0,
) -> dict[str, Any]:
    items = list(plan)
    statuses = Counter(item.status for item in items)
    reported_sources = Counter(
        item.candidate.reported_source
        for item in items
        if item.candidate.reported_source
    )
    return {
        "ok": True,
        "dry_run": dry_run,
        "arquivos_encontrados": len(items),
        "gtins_validos": sum(item.candidate.gtin is not None for item in items),
        "prontos_para_estagio": statuses.get(READY_STATUS, 0),
        "imagens_estagiadas": staged_images,
        "imagens_publicadas": 0,
        "produtos_criados": 0,
        "cadastros_de_lojas_alterados": 0,
        "fontes_informadas_no_relatorio": dict(sorted(reported_sources.items())),
        "por_status": dict(sorted(statuses.items())),
        "itens": [item.to_dict() for item in items],
    }


def _validate_staging_root(staging_dir: str | Path) -> Path:
    root = Path(staging_dir).expanduser().resolve()
    if root.name != DEFAULT_PROTECTED_STAGING_DIR.name:
        raise ValueError(
            "A pasta de estagio deve terminar em catalogo_mestre_pendente; "
            "esse prefixo nao e publicado pelo backend."
        )
    return root


def stage_image_import(
    db,
    plan: Iterable[CatalogImagePlanItem],
    *,
    source_ref: str,
    staging_dir: str | Path = DEFAULT_PROTECTED_STAGING_DIR,
) -> int:
    normalized_source_ref = source_ref.strip()
    if not normalized_source_ref or len(normalized_source_ref) > 300:
        raise ValueError("source_ref deve identificar a origem em ate 300 caracteres.")

    root = _validate_staging_root(staging_dir)
    root.mkdir(parents=True, exist_ok=True)
    insert_rows: list[dict[str, Any]] = []

    for item in plan:
        if item.status != READY_STATUS:
            continue
        candidate = item.candidate
        if not candidate.gtin or not candidate.sha256 or item.product_id is None:
            raise ValueError("Plano pronto contem candidato sem identidade completa.")

        extension = {
            "JPEG": ".jpg",
            "PNG": ".png",
            "WEBP": ".webp",
        }[str(candidate.image_format)]
        relative_path = Path(candidate.gtin) / f"{candidate.sha256}{extension}"
        destination = (root / relative_path).resolve()
        if not destination.is_relative_to(root):
            raise ValueError("Destino de estagio escapou da pasta protegida.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if _sha256(destination) != candidate.sha256:
                raise ValueError(f"Arquivo de estagio divergente: {destination}")
        else:
            shutil.copy2(candidate.path, destination)

        source_url = (
            f"usuario-ean://{quote(normalized_source_ref, safe='')}/{candidate.sha256}"
        )
        insert_rows.append(
            {
                "produto_id": item.product_id,
                "tipo_origem": "fornecida_usuario_ean",
                "url_origem": source_url,
                "arquivo_url": None,
                "hash_arquivo": candidate.sha256,
                "ordem": int(item.order or 0),
                "e_principal": False,
                "gerada_por_ia": False,
                "direitos_uso_status": "nao_verificado",
                "status_revisao": "pendente",
                "largura": candidate.width,
                "altura": candidate.height,
                "tamanho_bytes": candidate.size_bytes,
                "metadados": {
                    "nome_arquivo_original": candidate.filename,
                    "rotulo_arquivo": candidate.label,
                    "source_ref": normalized_source_ref,
                    "fonte_relatorio": candidate.reported_source,
                    "staging_path": str(
                        Path(DEFAULT_PROTECTED_STAGING_DIR.name) / relative_path
                    ).replace("\\", "/"),
                    "protegida_de_publicacao": True,
                },
                "ativo": False,
            }
        )

    if insert_rows:
        statement = text(
            """
            INSERT INTO catalogo_mestre_imagens (
                produto_id, tipo_origem, url_origem, arquivo_url, hash_arquivo,
                ordem, e_principal, gerada_por_ia, direitos_uso_status,
                status_revisao, largura, altura, tamanho_bytes, metadados, ativo
            ) VALUES (
                :produto_id, :tipo_origem, :url_origem, :arquivo_url,
                :hash_arquivo, :ordem, :e_principal, :gerada_por_ia,
                :direitos_uso_status, :status_revisao, :largura, :altura,
                :tamanho_bytes, :metadados, :ativo
            )
            """
        ).bindparams(bindparam("metadados", type_=JSON))
        db.execute(statement, insert_rows)
    return len(insert_rows)
