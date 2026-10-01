"""Importacao segura de produtos do relatorio de estoque do Excellent Sistemas.

O comando ``plan`` executa a substituicao inteira dentro de uma transacao e
desfaz tudo ao final. O ``apply`` aceita somente o PDF, banco, tenant e plano
imutavel que foram simulados. Produtos anteriores sao arquivados (soft delete),
preservando referencias historicas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

import pdfplumber
from sqlalchemy import func, insert, or_, select, update

from importar_simplesvet_plan import (
    ImportPlanError,
    database_identity,
    environment_name,
    is_production,
    load_plan,
    write_json,
)


PLAN_VERSION = 1
PLAN_TTL = timedelta(hours=24)
DEFAULT_EXPECTED_COUNT = 3643
DEFAULT_REPORT_DIR = (
    Path(__file__).resolve().parent.parent / "runtime" / "importacoes-excellent"
)
PRODUCTION_CONFIRMATION_PREFIX = "IMPORTAR-PRODUTOS-PRODUCAO"
ACTIVE_TENANT_STATUSES = {"active", "ativo", "trial"}

PRODUCT_LINE_RE = re.compile(
    r"^(?P<external>.+?)\s+\(Principal\)\s+"
    r"(?P<internal>.+?)\s+"
    r"(?P<stock>-?[0-9][0-9.,]*)\s*\|\s*"
    r"(?P<unit>\S+)\s+"
    r"(?P<minimum>-?[0-9][0-9.,]*)$"
)
FINANCIAL_LINE_RE = re.compile(
    r"^R\$\s+(?P<cost>[0-9.]+,[0-9]{2})\s+"
    r"(?P<cost_total>-?[0-9.,]+)\s+"
    r"R\$\s+(?P<sale>[0-9.]+,[0-9]{2})\s+"
    r"R\$\s+(?P<profit>-?[0-9.]+,[0-9]{2})$"
)


@dataclass(frozen=True)
class ExcellentProduct:
    source_code: str
    internal_code: str | None
    name: str
    source_name_missing: bool
    classification: str | None
    ncm: str | None
    unit: str
    stock: Decimal
    minimum_stock: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    sale_price: Decimal
    projected_profit: Decimal


class ExcellentImportError(ValueError):
    """Falha fechada na leitura ou validacao do relatorio."""


def _decimal(value: str) -> Decimal:
    normalized = str(value or "").strip().replace(" ", "")
    if not normalized:
        raise ExcellentImportError("Numero vazio no relatorio.")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ExcellentImportError(f"Numero invalido no relatorio: {value!r}.") from exc


def normalize_gtin(value: Any) -> str | None:
    gtin = str(value or "").strip()
    if not gtin.isdigit() or len(gtin) not in {8, 12, 13, 14}:
        return None
    total = 0
    weight = 3
    for char in reversed(gtin[:-1]):
        total += int(char) * weight
        weight = 1 if weight == 3 else 3
    expected = (10 - (total % 10)) % 10
    return gtin if expected == int(gtin[-1]) else None


def _normalize_ncm(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw or raw.casefold() == "s/r":
        return None
    digits = re.sub(r"\D", "", raw)
    return digits if len(digits) == 8 else None


def _clean_optional(value: str | None) -> str | None:
    cleaned = re.sub(r"\s+", " ", str(value or "")).strip()
    return None if not cleaned or cleaned.casefold() == "s/r" else cleaned


def _split_classification_ncm(line: str) -> tuple[str | None, str | None]:
    parts = str(line or "").strip().rsplit(" ", 1)
    if len(parts) != 2:
        raise ExcellentImportError(f"Linha de classificacao/NCM invalida: {line!r}.")
    return _clean_optional(parts[0]), _normalize_ncm(parts[1])


def parse_page_text(text_value: str, *, page_number: int) -> list[ExcellentProduct]:
    lines = [
        line.strip() for line in str(text_value or "").splitlines() if line.strip()
    ]
    starts = [index for index, line in enumerate(lines) if "(Principal)" in line]
    products: list[ExcellentProduct] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        block = lines[start:end]
        if len(block) < 4:
            raise ExcellentImportError(
                f"Pagina {page_number}: produto incompleto perto de {block[0]!r}."
            )
        product_match = PRODUCT_LINE_RE.fullmatch(block[0])
        financial_index = next(
            (
                index
                for index, line in enumerate(block[1:], start=1)
                if FINANCIAL_LINE_RE.fullmatch(line)
            ),
            None,
        )
        financial_match = (
            FINANCIAL_LINE_RE.fullmatch(block[financial_index])
            if financial_index is not None
            else None
        )
        if not product_match:
            raise ExcellentImportError(
                f"Pagina {page_number}: linha de produto invalida: {block[0]!r}."
            )
        if not financial_match:
            raise ExcellentImportError(
                f"Pagina {page_number}: linha financeira ausente perto de {block[0]!r}."
            )
        if financial_index is None or financial_index < 3:
            raise ExcellentImportError(
                f"Pagina {page_number}: bloco de produto incompleto perto de {block[0]!r}."
            )
        classification, ncm = _split_classification_ncm(block[financial_index - 1])
        raw_name = _clean_optional(" ".join(block[1 : financial_index - 1]))
        source_code = re.sub(r"\s+", " ", product_match.group("external")).strip()
        if not source_code:
            raise ExcellentImportError(f"Pagina {page_number}: codigo de origem vazio.")
        products.append(
            ExcellentProduct(
                source_code=source_code,
                internal_code=_clean_optional(product_match.group("internal")),
                name=raw_name or source_code,
                source_name_missing=raw_name is None,
                classification=classification,
                ncm=ncm,
                unit=product_match.group("unit").strip().upper(),
                stock=_decimal(product_match.group("stock")),
                minimum_stock=_decimal(product_match.group("minimum")),
                unit_cost=_decimal(financial_match.group("cost")),
                total_cost=_decimal(financial_match.group("cost_total")),
                sale_price=_decimal(financial_match.group("sale")),
                projected_profit=_decimal(financial_match.group("profit")),
            )
        )
    return products


def parse_report_pdf(path: Path) -> list[ExcellentProduct]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ExcellentImportError(f"PDF nao encontrado: {resolved}")
    products: list[ExcellentProduct] = []
    with pdfplumber.open(resolved) as report:
        if not report.pages:
            raise ExcellentImportError("PDF sem paginas.")
        for page_number, page in enumerate(report.pages, start=1):
            products.extend(
                parse_page_text(page.extract_text() or "", page_number=page_number)
            )
    if not products:
        raise ExcellentImportError("Nenhum produto reconhecido no PDF.")
    return products


def _sku_key(value: str) -> str:
    return value.strip().casefold()


def choose_skus(products: Iterable[ExcellentProduct]) -> list[str]:
    items = list(products)
    internal_counts = Counter(
        _sku_key(item.internal_code)
        for item in items
        if item.internal_code and len(item.internal_code) <= 50
    )
    used: set[str] = set()
    result: list[str] = []
    for index, item in enumerate(items, start=1):
        internal = (
            item.internal_code
            if item.internal_code and len(item.internal_code) <= 50
            else None
        )
        if internal and internal_counts[_sku_key(internal)] == 1:
            candidate = internal
        else:
            candidate = item.source_code[:50].strip()
        if not candidate:
            candidate = f"EX-{index}"
        base = candidate[:50]
        suffix_index = 1
        while _sku_key(candidate) in used:
            suffix = f"-{suffix_index}"
            candidate = f"{base[: 50 - len(suffix)]}{suffix}"
            suffix_index += 1
        used.add(_sku_key(candidate))
        result.append(candidate)
    return result


def report_signature(products: Iterable[ExcellentProduct]) -> str:
    payload = []
    for item in products:
        row = asdict(item)
        for key, value in tuple(row.items()):
            if isinstance(value, Decimal):
                row[key] = format(value, "f")
        payload.append(row)
    return _sha256_json(payload)


def summarize_products(products: list[ExcellentProduct]) -> dict[str, Any]:
    skus = choose_skus(products)
    if len({_sku_key(value) for value in skus}) != len(products):
        raise ExcellentImportError("Nao foi possivel gerar SKUs unicos.")
    source_codes = Counter(_sku_key(item.source_code) for item in products)
    duplicate_source_codes = sum(1 for count in source_codes.values() if count > 1)
    if duplicate_source_codes:
        raise ExcellentImportError(
            f"Relatorio possui {duplicate_source_codes} codigos de origem duplicados."
        )
    internal_codes = Counter(
        _sku_key(item.internal_code) for item in products if item.internal_code
    )
    return {
        "products": len(products),
        "valid_gtins": sum(
            normalize_gtin(item.source_code) is not None for item in products
        ),
        "source_names_missing": sum(item.source_name_missing for item in products),
        "internal_codes_missing": sum(item.internal_code is None for item in products),
        "duplicate_internal_code_values": sum(
            1 for count in internal_codes.values() if count > 1
        ),
        "zero_unit_cost": sum(item.unit_cost == 0 for item in products),
        "negative_stock": sum(item.stock < 0 for item in products),
        "positive_stock": sum(item.stock > 0 for item in products),
        "zero_stock": sum(item.stock == 0 for item in products),
        "stock_quantity_total": format(
            sum((item.stock for item in products), Decimal(0)), "f"
        ),
        "inventory_cost_total": format(
            sum((item.total_cost for item in products), Decimal(0)), "f"
        ),
        "report_signature": report_signature(products),
    }


def _scan_barcode(value: str) -> str | None:
    cleaned = value.strip()
    return (
        cleaned if 1 <= len(cleaned) <= 20 and not re.search(r"\s", cleaned) else None
    )


def build_product_rows(
    products: list[ExcellentProduct], *, tenant_id: str, user_id: int
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item, sku in zip(products, choose_skus(products), strict=True):
        gtin = normalize_gtin(item.source_code)
        unit = "UN" if item.unit == "UND" else item.unit[:10]
        rows.append(
            {
                "tenant_id": UUID(tenant_id),
                "user_id": int(user_id),
                "codigo": sku,
                "nome": item.name[:200],
                "tipo": "produto",
                "situacao": True,
                "tipo_produto": "SIMPLES",
                "is_parent": False,
                "is_sellable": True,
                "codigo_barras": _scan_barcode(item.source_code),
                "preco_custo": float(item.unit_cost),
                "preco_venda": float(item.sale_price),
                "estoque_atual": float(item.stock),
                "estoque_minimo": float(item.minimum_stock),
                "estoque_fisico": float(item.stock),
                "estoque_ecommerce": float(item.stock),
                "unidade": unit or "UN",
                "e_granel": bool(
                    item.classification and "granel" in item.classification.casefold()
                ),
                "participa_sugestao_compra": True,
                "ncm": item.ncm,
                "gtin_ean": gtin,
                "gtin_ean_tributario": gtin,
                "anunciar_ecommerce": False,
                "anunciar_app": False,
                "auto_classificar_nome": True,
                "ativo": True,
                "deleted_at": None,
            }
        )
    return rows


def _normalize_tenant_id(value: str) -> str:
    try:
        return str(UUID(str(value).strip()))
    except (TypeError, ValueError) as exc:
        raise ImportPlanError("tenant-id deve ser um UUID valido.") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _plan_material(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "plan_id"}


def _resolve_target(db, *, tenant_id: str, user_id: int) -> dict[str, Any]:
    from sqlalchemy import text

    from app.tenancy.context import tenant_context
    from app.tenancy.rls import sync_rls_tenant

    with tenant_context(tenant_id):
        sync_rls_tenant(db, tenant_id)
        row = (
            db.execute(
                text(
                    """
                    SELECT CAST(t.id AS TEXT) AS tenant_id,
                           t.name AS tenant_name,
                           t.status AS tenant_status,
                           u.id AS user_id,
                           u.email AS user_email,
                           u.is_active AS user_active
                    FROM tenants t
                    JOIN users u ON CAST(u.tenant_id AS TEXT) = CAST(t.id AS TEXT)
                    WHERE CAST(t.id AS TEXT) = :tenant_id
                      AND u.id = :user_id
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id, "user_id": user_id},
            )
            .mappings()
            .first()
        )
    if not row:
        raise ImportPlanError(
            "Empresa/usuario de destino nao encontrados ou nao pertencem um ao outro."
        )
    status = str(row["tenant_status"] or "").strip().lower()
    if status not in ACTIVE_TENANT_STATUSES:
        raise ImportPlanError(f"Empresa de destino nao esta ativa (status={status}).")
    if not bool(row["user_active"]):
        raise ImportPlanError("Usuario de destino esta inativo.")
    return {
        "tenant_id": str(row["tenant_id"]),
        "tenant_name": str(row["tenant_name"]),
        "tenant_status": status,
        "user_id": int(row["user_id"]),
        "user_email": str(row["user_email"]),
    }


def _run_replacement(
    db,
    *,
    products: list[ExcellentProduct],
    tenant_id: str,
    user_id: int,
    source_tenant_id: str,
    pdf_sha256: str,
    dry_run: bool,
    expected_stable: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from app.produtos_catalogo_models import Produto
    from app.services.base_catalog_enrichment_service import (
        enrich_existing_products_by_gtin,
    )
    from app.tenancy.context import tenant_context
    from app.tenancy.rls import sync_rls_tenant

    rows = build_product_rows(products, tenant_id=tenant_id, user_id=user_id)
    incoming_skus = sorted({_sku_key(row["codigo"]) for row in rows})
    archive_prefix = f"ARQ-{pdf_sha256[:8]}-"
    now = datetime.now(timezone.utc)
    with tenant_context(tenant_id):
        sync_rls_tenant(db, tenant_id)
        active_before = int(
            db.execute(
                select(func.count(Produto.id)).where(
                    Produto.tenant_id == UUID(tenant_id),
                    Produto.deleted_at.is_(None),
                )
            ).scalar_one()
        )
        collision_before = int(
            db.execute(
                select(func.count(Produto.id)).where(
                    Produto.tenant_id == UUID(tenant_id),
                    func.lower(func.trim(Produto.codigo)).in_(incoming_skus),
                )
            ).scalar_one()
        )
        archived = db.execute(
            update(Produto)
            .where(
                Produto.tenant_id == UUID(tenant_id),
                or_(
                    Produto.deleted_at.is_(None),
                    func.lower(func.trim(Produto.codigo)).in_(incoming_skus),
                ),
            )
            .values(
                codigo=func.concat(archive_prefix, Produto.id),
                situacao=False,
                ativo=False,
                deleted_at=func.coalesce(Produto.deleted_at, now),
                updated_at=now,
            )
        ).rowcount
        db.execute(insert(Produto), rows)
        db.flush()

    bundle_code = f"excellent-produtos-ean-{pdf_sha256[:12]}"
    enrichment = enrich_existing_products_by_gtin(
        db=db,
        source_tenant_id=source_tenant_id,
        target_tenant_id=tenant_id,
        user_id=user_id,
        dry_run=dry_run,
        bundle_code=bundle_code,
        bundle_version="v1",
    )
    summary = summarize_products(products)
    result = {
        "active_products_before": active_before,
        "existing_sku_collisions": collision_before,
        "archived_or_rekeyed_products": int(archived or 0),
        "created_products": len(rows),
        "product_data": summary,
        "base_catalog_enrichment": enrichment,
        "channels_published": 0,
    }
    if not dry_run and expected_stable is not None:
        current_stable = _stable_result(result)
        if current_stable != expected_stable:
            db.rollback()
            raise ImportPlanError(
                "O resultado mudou desde a simulacao; nada foi aplicado. "
                "Gere um novo plano."
            )
    if dry_run:
        db.rollback()
    else:
        db.commit()
    return result


def _stable_result(result: dict[str, Any]) -> dict[str, Any]:
    enrichment = result.get("base_catalog_enrichment") or {}
    image_count = (
        enrichment.get("would_copy_images")
        if enrichment.get("dry_run")
        else enrichment.get("copied_images")
    )
    return {
        "active_products_before": result.get("active_products_before"),
        "existing_sku_collisions": result.get("existing_sku_collisions"),
        "created_products": result.get("created_products"),
        "product_data": result.get("product_data"),
        "matched_products": enrichment.get("matched_products"),
        "compatible_products": enrichment.get("compatible_products"),
        "incompatible_products": enrichment.get("incompatible_products"),
        "source_ambiguous_gtins": enrichment.get("source_ambiguous_gtins"),
        "target_ambiguous_gtins": enrichment.get("target_ambiguous_gtins"),
        "source_invalid_gtins": enrichment.get("source_invalid_gtins"),
        "target_invalid_gtins": enrichment.get("target_invalid_gtins"),
        "images": image_count,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Substitui produtos pelo PDF do Excellent com simulacao obrigatoria."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser("plan", help="Simula e gera um plano imutavel.")
    plan.add_argument("--tenant-id", required=True)
    plan.add_argument("--user-id", required=True, type=int)
    plan.add_argument("--source-tenant-id", required=True)
    plan.add_argument("--pdf", required=True, type=Path)
    plan.add_argument("--expected-count", type=int, default=DEFAULT_EXPECTED_COUNT)
    plan.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)

    apply = commands.add_parser("apply", help="Aplica um plano ainda valido.")
    apply.add_argument("--plan-file", required=True, type=Path)
    apply.add_argument("--confirm-tenant-id", required=True)
    apply.add_argument("--confirm-plan-id", required=True)
    apply.add_argument("--allow-production-apply", action="store_true")
    apply.add_argument("--confirm-production")
    apply.add_argument("--backup-reference")
    return parser


def _create_plan(
    *,
    database: dict[str, Any],
    environment: str,
    target: dict[str, Any],
    source_tenant_id: str,
    pdf_path: Path,
    pdf_sha256: str,
    expected_count: int,
    simulation: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "version": PLAN_VERSION,
        "status": "simulation_approved",
        "created_at": now.isoformat(),
        "expires_at": (now + PLAN_TTL).isoformat(),
        "environment": environment,
        "database": database,
        "target": target,
        "source_tenant_id": source_tenant_id,
        "pdf": {
            "path": str(pdf_path),
            "sha256": pdf_sha256,
            "bytes": pdf_path.stat().st_size,
        },
        "expected_count": expected_count,
        "simulation": simulation,
        "simulation_stable": _stable_result(simulation),
    }
    payload["plan_id"] = _sha256_json(_plan_material(payload))
    return payload


def _validate_plan(
    payload: dict[str, Any],
    *,
    database: dict[str, Any],
    confirm_tenant_id: str,
    confirm_plan_id: str,
) -> tuple[Path, str, str, int]:
    if payload.get("version") != PLAN_VERSION:
        raise ImportPlanError("Versao do plano nao suportada.")
    if payload.get("status") != "simulation_approved":
        raise ImportPlanError("O plano nao registra uma simulacao aprovada.")
    expected_plan_id = _sha256_json(_plan_material(payload))
    if payload.get("plan_id") != expected_plan_id:
        raise ImportPlanError("O plano foi alterado depois da simulacao.")
    if confirm_plan_id != expected_plan_id:
        raise ImportPlanError("A confirmacao do plan_id nao corresponde ao plano.")
    tenant_id = _normalize_tenant_id(payload["target"]["tenant_id"])
    if confirm_tenant_id != tenant_id:
        raise ImportPlanError("A confirmacao da empresa nao corresponde ao plano.")
    if payload["database"].get("fingerprint") != database.get("fingerprint"):
        raise ImportPlanError("O plano foi criado para outro banco de dados.")
    try:
        expires_at = datetime.fromisoformat(str(payload["expires_at"]))
    except (KeyError, ValueError) as exc:
        raise ImportPlanError("Plano sem validade reconhecivel.") from exc
    if datetime.now(timezone.utc) > expires_at:
        raise ImportPlanError("O plano expirou; gere uma nova simulacao.")
    pdf_path = Path(payload["pdf"]["path"]).resolve()
    if not pdf_path.is_file() or _sha256_file(pdf_path) != payload["pdf"]["sha256"]:
        raise ImportPlanError("O PDF mudou depois da simulacao.")
    return (
        pdf_path,
        _normalize_tenant_id(payload["source_tenant_id"]),
        tenant_id,
        int(payload["target"]["user_id"]),
    )


def _plan_command(args, *, database, environment, session_factory) -> int:
    tenant_id = _normalize_tenant_id(args.tenant_id)
    source_tenant_id = _normalize_tenant_id(args.source_tenant_id)
    if tenant_id == source_tenant_id:
        raise ImportPlanError("Tenant fonte e destino nao podem ser iguais.")
    if args.expected_count <= 0:
        raise ImportPlanError("expected-count deve ser maior que zero.")
    pdf_path = args.pdf.expanduser().resolve()
    pdf_sha256 = _sha256_file(pdf_path)
    products = parse_report_pdf(pdf_path)
    if len(products) != args.expected_count:
        raise ImportPlanError(
            f"Esperados {args.expected_count} produtos, mas o PDF possui {len(products)}."
        )

    db = session_factory()
    try:
        target = _resolve_target(db, tenant_id=tenant_id, user_id=args.user_id)
        simulation = _run_replacement(
            db,
            products=products,
            tenant_id=tenant_id,
            user_id=args.user_id,
            source_tenant_id=source_tenant_id,
            pdf_sha256=pdf_sha256,
            dry_run=True,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    plan = _create_plan(
        database=database,
        environment=environment,
        target=target,
        source_tenant_id=source_tenant_id,
        pdf_path=pdf_path,
        pdf_sha256=pdf_sha256,
        expected_count=args.expected_count,
        simulation=simulation,
    )
    report_dir = args.report_dir.expanduser().resolve()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    plan_path = report_dir / f"excellent-plan-{timestamp}-{plan['plan_id'][:12]}.json"
    write_json(plan_path, plan)
    print(
        json.dumps(
            {
                "ok": True,
                "mode": "plan",
                "dry_run": True,
                "tenant": target,
                "plan_id": plan["plan_id"],
                "plan_file": str(plan_path),
                "expires_at": plan["expires_at"],
                "simulation": simulation,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _apply_command(args, *, database, environment, session_factory) -> int:
    plan_path = args.plan_file.expanduser().resolve()
    plan = load_plan(plan_path)
    confirm_tenant_id = _normalize_tenant_id(args.confirm_tenant_id)
    pdf_path, source_tenant_id, tenant_id, user_id = _validate_plan(
        plan,
        database=database,
        confirm_tenant_id=confirm_tenant_id,
        confirm_plan_id=args.confirm_plan_id,
    )
    production = is_production(environment, database)
    if production and not args.allow_production_apply:
        raise ImportPlanError(
            "Apply em producao bloqueado sem --allow-production-apply."
        )
    expected_confirmation = f"{PRODUCTION_CONFIRMATION_PREFIX}-{tenant_id}"
    if production and args.confirm_production != expected_confirmation:
        raise ImportPlanError("Confirmacao de producao ausente ou incorreta.")
    if production and not str(args.backup_reference or "").strip():
        raise ImportPlanError("Apply em producao exige --backup-reference.")

    marker_path = plan_path.parent / f"excellent-applied-{plan['plan_id']}.json"
    if marker_path.exists():
        raise ImportPlanError("Este plano ja foi aplicado; gere uma nova simulacao.")
    lock_path = plan_path.parent / f"excellent-applying-{plan['plan_id']}.lock"
    try:
        with lock_path.open("x", encoding="utf-8") as lock_file:
            lock_file.write(plan["plan_id"] + "\n")
    except FileExistsError as exc:
        raise ImportPlanError(
            "Este plano ja esta sendo aplicado ou exige auditoria."
        ) from exc

    products = parse_report_pdf(pdf_path)
    if len(products) != int(plan["expected_count"]):
        lock_path.unlink(missing_ok=True)
        raise ImportPlanError("A contagem atual do PDF diverge do plano.")
    if (
        report_signature(products)
        != plan["simulation"]["product_data"]["report_signature"]
    ):
        lock_path.unlink(missing_ok=True)
        raise ImportPlanError("O conteudo interpretado do PDF diverge do plano.")

    db = session_factory()
    try:
        target = _resolve_target(db, tenant_id=tenant_id, user_id=user_id)
        preflight = _run_replacement(
            db,
            products=products,
            tenant_id=tenant_id,
            user_id=user_id,
            source_tenant_id=source_tenant_id,
            pdf_sha256=plan["pdf"]["sha256"],
            dry_run=True,
        )
        if _stable_result(preflight) != plan["simulation_stable"]:
            raise ImportPlanError(
                "A base mudou desde a simulacao; nada foi aplicado. Gere um novo plano."
            )
        result = _run_replacement(
            db,
            products=products,
            tenant_id=tenant_id,
            user_id=user_id,
            source_tenant_id=source_tenant_id,
            pdf_sha256=plan["pdf"]["sha256"],
            dry_run=False,
            expected_stable=plan["simulation_stable"],
        )
    except Exception:
        db.rollback()
        lock_path.unlink(missing_ok=True)
        raise
    finally:
        db.close()

    stable_result = _stable_result(result)
    matches_simulation = stable_result == plan["simulation_stable"]
    receipt = {
        "ok": True,
        "mode": "apply",
        "dry_run": False,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "plan_id": plan["plan_id"],
        "plan_file": str(plan_path),
        "tenant": target,
        "backup_reference": str(args.backup_reference or "").strip() or None,
        "result": result,
        "simulation_stable": plan["simulation_stable"],
        "matches_simulation": matches_simulation,
    }
    try:
        write_json(marker_path, receipt)
    except OSError as exc:
        receipt["report_warning"] = (
            "A importacao foi confirmada, mas o recibo local falhou; "
            f"o bloqueio foi mantido: {exc}"
        )
    else:
        lock_path.unlink(missing_ok=True)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _fail(message: str, *, mode: str) -> int:
    print(
        json.dumps(
            {"ok": False, "mode": mode, "error": message},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        # O CLI nao passa pelo bootstrap da API. Carregar o registro completo antes
        # de abrir a sessao garante que relacionamentos por nome (User, Cliente,
        # EstoqueMovimentacao etc.) estejam disponiveis ao configurar os mappers.
        from app.db import base as _orm_registry  # noqa: F401
        from app.db import DATABASE_URL, SessionLocal

        database = database_identity(DATABASE_URL)
        environment = environment_name()
        if args.command == "plan":
            return _plan_command(
                args,
                database=database,
                environment=environment,
                session_factory=SessionLocal,
            )
        return _apply_command(
            args,
            database=database,
            environment=environment,
            session_factory=SessionLocal,
        )
    except (ExcellentImportError, ImportPlanError, ValueError) as exc:
        return _fail(str(exc), mode=args.command)
    except Exception as exc:
        return _fail(f"Falha inesperada: {exc}", mode=args.command)


if __name__ == "__main__":
    raise SystemExit(main())
