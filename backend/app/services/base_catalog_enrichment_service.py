"""Enriquece produtos existentes usando o catalogo-base e GTIN/EAN.

O fluxo nunca cria produtos e nunca copia campos comerciais ou operacionais.
Somente correspondencias unicas, com GTIN valido nos dois tenants, podem ser
usadas. Campos ja preenchidos no tenant destino sao preservados.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.base_catalog_import_catalog import _create_category
from app.services.base_catalog_import_core import (
    _insert_and_lookup,
    _record_install,
    _record_mapping,
    _select_rows,
    _validate_tenants,
)
from app.services.base_catalog_import_images import (
    _create_product_image,
    copy_product_image_url,
)
from app.tenancy.rls import sync_rls_tenant


DEFAULT_EAN_ENRICHMENT_BUNDLE_CODE = "catalogo-base-enriquecimento-ean"
DEFAULT_EAN_ENRICHMENT_BUNDLE_VERSION = "v1"
USELESS_CATEGORY_NAMES = {"a classificar", "sem categoria", "nao classificado"}

# Lista positiva. Preco, custo, margem, estoque, fornecedor, promocao, comissao,
# desconto e configuracoes de publicacao nao fazem parte deste contrato.
SAFE_PRODUCT_FIELDS = (
    "descricao_curta",
    "descricao_completa",
    "ncm",
    "cest",
    "gtin_ean",
    "gtin_ean_tributario",
    "origem",
    "perfil_tributario",
    "forma_aquisicao",
    "tipo_item",
    "percentual_tributos",
    "cfop",
    "aliquota_icms",
    "aliquota_pis",
    "aliquota_cofins",
    "informacoes_adicionais_nf",
    "peso_liquido",
    "peso_bruto",
    "largura",
    "altura",
    "profundidade",
    "volume",
    "itens_por_caixa",
    "peso_embalagem",
    "classificacao_racao",
    "categoria_racao",
    "especie_compativel",
    "especies_indicadas",
    "sabor_proteina",
    "subcategoria",
    "tags",
)


class BaseCatalogEnrichmentError(RuntimeError):
    pass


@dataclass
class BaseCatalogEnrichmentResult:
    source_tenant_id: str
    target_tenant_id: str
    dry_run: bool
    bundle_code: str = DEFAULT_EAN_ENRICHMENT_BUNDLE_CODE
    bundle_version: str = DEFAULT_EAN_ENRICHMENT_BUNDLE_VERSION
    matched_products: int = 0
    updated_products: int = 0
    would_update_products: int = 0
    copied_images: int = 0
    would_copy_images: int = 0
    source_ambiguous_gtins: int = 0
    target_ambiguous_gtins: int = 0
    source_invalid_gtins: int = 0
    target_invalid_gtins: int = 0
    fields: Counter[str] = field(default_factory=Counter)
    entities_created: Counter[str] = field(default_factory=Counter)
    entities_reused: Counter[str] = field(default_factory=Counter)
    samples: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # Compatibilidade com o registro de instalacao do catalogo-base.
    created: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)
    would_create: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": not self.errors,
            "source_tenant_id": self.source_tenant_id,
            "target_tenant_id": self.target_tenant_id,
            "dry_run": self.dry_run,
            "bundle_code": self.bundle_code,
            "bundle_version": self.bundle_version,
            "matched_products": self.matched_products,
            "updated_products": self.updated_products,
            "would_update_products": self.would_update_products,
            "copied_images": self.copied_images,
            "would_copy_images": self.would_copy_images,
            "source_ambiguous_gtins": self.source_ambiguous_gtins,
            "target_ambiguous_gtins": self.target_ambiguous_gtins,
            "source_invalid_gtins": self.source_invalid_gtins,
            "target_invalid_gtins": self.target_invalid_gtins,
            "fields": dict(sorted(self.fields.items())),
            "entities_created": dict(sorted(self.entities_created.items())),
            "entities_reused": dict(sorted(self.entities_reused.items())),
            "samples": self.samples,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def _text_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", normalized.casefold()).strip()


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


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


def _unique_rows_by_gtin(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], int, int]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invalid = 0
    for row in rows:
        if row.get("deleted_at") is not None:
            continue
        raw = str(row.get("codigo_barras") or "").strip()
        if not raw:
            continue
        gtin = normalize_gtin(raw)
        if gtin is None:
            invalid += 1
            continue
        grouped[gtin].append(row)
    ambiguous = sum(1 for items in grouped.values() if len(items) > 1)
    unique = {gtin: items[0] for gtin, items in grouped.items() if len(items) == 1}
    return unique, ambiguous, invalid


def _digits_with_length(value: Any, length: int) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits if len(digits) == length else None


def _safe_source_value(field_name: str, value: Any) -> Any:
    if _is_missing(value):
        return None
    if field_name == "ncm":
        return _digits_with_length(value, 8)
    if field_name == "cest":
        return _digits_with_length(value, 7)
    if field_name in {"gtin_ean", "gtin_ean_tributario"}:
        return normalize_gtin(value)
    if field_name == "origem":
        cleaned = str(value).strip()
        return cleaned if cleaned in set("012345678") else None
    if field_name == "cfop":
        return _digits_with_length(value, 4)
    return value


def plan_product_scalar_updates(
    source: dict[str, Any], target: dict[str, Any]
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for field_name in SAFE_PRODUCT_FIELDS:
        if not _is_missing(target.get(field_name)):
            continue
        value = _safe_source_value(field_name, source.get(field_name))
        if not _is_missing(value):
            updates[field_name] = value
    return updates


def _active_rows(db: Session, table_name: str, tenant_id: str) -> list[dict[str, Any]]:
    rows = _select_rows(db, table_name, tenant_id)
    return [row for row in rows if row.get("deleted_at") is None]


def _rows_by_id(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(row["id"]): row for row in rows}


def _rows_by_name(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _text_key(row.get("nome"))
        if key:
            result.setdefault(key, row)
    return result


def _useful_named_row(
    row_id: Any,
    rows: dict[int, dict[str, Any]],
    *,
    reject_names: set[str] | None = None,
) -> dict[str, Any] | None:
    if not row_id:
        return None
    row = rows.get(int(row_id))
    if not row or not _text_key(row.get("nome")):
        return None
    if reject_names and _text_key(row.get("nome")) in reject_names:
        return None
    return row


def _target_category_is_missing(
    target: dict[str, Any], target_categories: dict[int, dict[str, Any]]
) -> bool:
    if not target.get("categoria_id"):
        return True
    category = target_categories.get(int(target["categoria_id"])) or {}
    return _text_key(category.get("nome")) in USELESS_CATEGORY_NAMES


def _create_named_entity(
    db: Session,
    *,
    table_name: str,
    source_row: dict[str, Any],
    target_tenant_id: str,
    user_id: int,
) -> int:
    values = dict(source_row)
    values.update({"tenant_id": target_tenant_id, "user_id": user_id})
    return _insert_and_lookup(
        db,
        table_name=table_name,
        values=values,
        lookup_sql=f"""
            SELECT id FROM {table_name}
            WHERE CAST(tenant_id AS TEXT)=:tenant_id
              AND lower(trim(nome))=lower(trim(:nome))
            LIMIT 1
        """,
        lookup_params={"tenant_id": target_tenant_id, "nome": source_row["nome"]},
    )


def _ensure_department_or_brand(
    db: Session,
    *,
    table_name: str,
    item_type: str,
    source_row: dict[str, Any],
    target_by_name: dict[str, dict[str, Any]],
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogEnrichmentResult,
) -> int:
    key = _text_key(source_row["nome"])
    existing = target_by_name.get(key)
    if existing:
        result.entities_reused[table_name] += 1
        target_id = int(existing["id"])
        _record_mapping(
            db,
            tenant_id=target_tenant_id,
            user_id=user_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type=item_type,
            source_id=int(source_row["id"]),
            target_table=table_name,
            target_id=target_id,
        )
        return target_id
    target_id = _create_named_entity(
        db,
        table_name=table_name,
        source_row=source_row,
        target_tenant_id=target_tenant_id,
        user_id=user_id,
    )
    target_by_name[key] = {"id": target_id, "nome": source_row["nome"]}
    result.entities_created[table_name] += 1
    _record_mapping(
        db,
        tenant_id=target_tenant_id,
        user_id=user_id,
        bundle_code=result.bundle_code,
        bundle_version=result.bundle_version,
        item_type=item_type,
        source_id=int(source_row["id"]),
        target_table=table_name,
        target_id=target_id,
    )
    return target_id


def _ensure_category(
    db: Session,
    *,
    source_row: dict[str, Any],
    target_department_id: int | None,
    target_by_name: dict[str, dict[str, Any]],
    target_tenant_id: str,
    user_id: int,
    result: BaseCatalogEnrichmentResult,
) -> int:
    key = _text_key(source_row["nome"])
    existing = target_by_name.get(key)
    if existing:
        result.entities_reused["categorias"] += 1
        target_id = int(existing["id"])
        _record_mapping(
            db,
            tenant_id=target_tenant_id,
            user_id=user_id,
            bundle_code=result.bundle_code,
            bundle_version=result.bundle_version,
            item_type="categoria_ean",
            source_id=int(source_row["id"]),
            target_table="categorias",
            target_id=target_id,
        )
        return target_id
    target_id = _create_category(
        db,
        row=source_row,
        target_tenant_id=target_tenant_id,
        user_id=user_id,
        target_department_id=target_department_id,
    )
    target_by_name[key] = {"id": target_id, "nome": source_row["nome"]}
    result.entities_created["categorias"] += 1
    _record_mapping(
        db,
        tenant_id=target_tenant_id,
        user_id=user_id,
        bundle_code=result.bundle_code,
        bundle_version=result.bundle_version,
        item_type="categoria_ean",
        source_id=int(source_row["id"]),
        target_table="categorias",
        target_id=target_id,
    )
    return target_id


def _update_target_product(
    db: Session,
    *,
    target_tenant_id: str,
    target_product_id: int,
    updates: dict[str, Any],
) -> None:
    if not updates:
        return
    values = dict(updates)
    values.update(
        {
            "tenant_id": target_tenant_id,
            "target_product_id": target_product_id,
            "updated_at": datetime.now(timezone.utc),
        }
    )
    assignments = ", ".join(f"{field}=:{field}" for field in updates)
    sync_rls_tenant(db, target_tenant_id)
    db.execute(
        text(
            f"""
            UPDATE produtos
               SET {assignments}, updated_at=:updated_at
             WHERE id=:target_product_id
               AND CAST(tenant_id AS TEXT)=:tenant_id
            """
        ),
        values,
    )


def _main_source_image(
    source_product: dict[str, Any], source_images: list[dict[str, Any]]
) -> dict[str, Any] | None:
    main_url = str(source_product.get("imagem_principal") or "").strip()
    if main_url:
        for row in source_images:
            if str(row.get("url") or "").strip() == main_url:
                return row
    for row in source_images:
        if row.get("e_principal"):
            return row
    return source_images[0] if len(source_images) == 1 else None


def enrich_existing_products_by_gtin(
    *,
    db: Session,
    source_tenant_id: str,
    target_tenant_id: str,
    user_id: int,
    dry_run: bool = True,
    bundle_code: str = DEFAULT_EAN_ENRICHMENT_BUNDLE_CODE,
    bundle_version: str = DEFAULT_EAN_ENRICHMENT_BUNDLE_VERSION,
) -> dict[str, Any]:
    _validate_tenants(db, source_tenant_id, target_tenant_id)
    result = BaseCatalogEnrichmentResult(
        source_tenant_id=source_tenant_id,
        target_tenant_id=target_tenant_id,
        dry_run=bool(dry_run),
        bundle_code=bundle_code,
        bundle_version=bundle_version,
    )

    source_products = [
        row
        for row in _active_rows(db, "produtos", source_tenant_id)
        if row.get("ativo") is not False and row.get("situacao") is not False
    ]
    target_products = _active_rows(db, "produtos", target_tenant_id)
    source_unique, source_ambiguous, source_invalid = _unique_rows_by_gtin(
        source_products
    )
    target_unique, target_ambiguous, target_invalid = _unique_rows_by_gtin(
        target_products
    )
    matches = [
        (source_unique[gtin], target_unique[gtin], gtin)
        for gtin in sorted(set(source_unique) & set(target_unique))
    ]
    result.matched_products = len(matches)
    result.source_ambiguous_gtins = source_ambiguous
    result.target_ambiguous_gtins = target_ambiguous
    result.source_invalid_gtins = source_invalid
    result.target_invalid_gtins = target_invalid

    source_departments = _rows_by_id(
        _active_rows(db, "departamentos", source_tenant_id)
    )
    source_categories = _rows_by_id(_active_rows(db, "categorias", source_tenant_id))
    source_brands = _rows_by_id(_active_rows(db, "marcas", source_tenant_id))
    target_department_rows = _active_rows(db, "departamentos", target_tenant_id)
    target_category_rows = _active_rows(db, "categorias", target_tenant_id)
    target_brand_rows = _active_rows(db, "marcas", target_tenant_id)
    target_categories = _rows_by_id(target_category_rows)
    target_departments_by_name = _rows_by_name(target_department_rows)
    target_categories_by_name = _rows_by_name(target_category_rows)
    target_brands_by_name = _rows_by_name(target_brand_rows)

    source_image_rows = _active_rows(db, "produto_imagens", source_tenant_id)
    target_image_rows = _active_rows(db, "produto_imagens", target_tenant_id)
    source_images: dict[int, list[dict[str, Any]]] = defaultdict(list)
    target_images: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in source_image_rows:
        source_images[int(row["produto_id"])].append(row)
    for row in target_image_rows:
        target_images[int(row["produto_id"])].append(row)

    planned_entities: dict[str, set[str]] = defaultdict(set)
    for source, target, gtin in matches:
        scalar_updates = plan_product_scalar_updates(source, target)
        for field_name in scalar_updates:
            result.fields[field_name] += 1

        source_department = _useful_named_row(
            source.get("departamento_id"), source_departments
        )
        source_category = _useful_named_row(
            source.get("categoria_id"),
            source_categories,
            reject_names=USELESS_CATEGORY_NAMES,
        )
        source_brand = _useful_named_row(source.get("marca_id"), source_brands)
        entity_updates: dict[str, Any] = {}

        if source_department and not target.get("departamento_id"):
            result.fields["departamento_id"] += 1
            department_key = _text_key(source_department["nome"])
            if department_key not in target_departments_by_name:
                planned_entities["departamentos"].add(department_key)
            if not dry_run:
                entity_updates["departamento_id"] = _ensure_department_or_brand(
                    db,
                    table_name="departamentos",
                    item_type="departamento_ean",
                    source_row=source_department,
                    target_by_name=target_departments_by_name,
                    target_tenant_id=target_tenant_id,
                    user_id=user_id,
                    result=result,
                )

        if source_brand and not target.get("marca_id"):
            result.fields["marca_id"] += 1
            brand_key = _text_key(source_brand["nome"])
            if brand_key not in target_brands_by_name:
                planned_entities["marcas"].add(brand_key)
            if not dry_run:
                entity_updates["marca_id"] = _ensure_department_or_brand(
                    db,
                    table_name="marcas",
                    item_type="marca_ean",
                    source_row=source_brand,
                    target_by_name=target_brands_by_name,
                    target_tenant_id=target_tenant_id,
                    user_id=user_id,
                    result=result,
                )

        if source_category and _target_category_is_missing(target, target_categories):
            result.fields["categoria_id"] += 1
            category_key = _text_key(source_category["nome"])
            if category_key not in target_categories_by_name:
                planned_entities["categorias"].add(category_key)
            if not dry_run:
                target_department_id = entity_updates.get("departamento_id")
                if not target_department_id and target.get("departamento_id"):
                    target_department_id = int(target["departamento_id"])
                if not target_department_id and source_department:
                    target_department_id = _ensure_department_or_brand(
                        db,
                        table_name="departamentos",
                        item_type="departamento_ean",
                        source_row=source_department,
                        target_by_name=target_departments_by_name,
                        target_tenant_id=target_tenant_id,
                        user_id=user_id,
                        result=result,
                    )
                    entity_updates.setdefault("departamento_id", target_department_id)
                entity_updates["categoria_id"] = _ensure_category(
                    db,
                    source_row=source_category,
                    target_department_id=target_department_id,
                    target_by_name=target_categories_by_name,
                    target_tenant_id=target_tenant_id,
                    user_id=user_id,
                    result=result,
                )

        source_image = _main_source_image(
            source, source_images.get(int(source["id"]), [])
        )
        can_copy_image = bool(
            source_image
            and _is_missing(target.get("imagem_principal"))
            and not target_images.get(int(target["id"]))
        )
        has_updates = (
            bool(scalar_updates or entity_updates)
            if not dry_run
            else bool(
                scalar_updates
                or (source_department and not target.get("departamento_id"))
                or (source_brand and not target.get("marca_id"))
                or (
                    source_category
                    and _target_category_is_missing(target, target_categories)
                )
            )
        )
        if can_copy_image:
            result.fields["imagem_principal"] += 1
            if dry_run:
                result.would_copy_images += 1
            else:
                new_url = copy_product_image_url(
                    str(source_image["url"]),
                    source_tenant_id=source_tenant_id,
                    source_product_id=int(source["id"]),
                    target_tenant_id=target_tenant_id,
                    target_product_id=int(target["id"]),
                )
                target_image_id = _create_product_image(
                    db,
                    row=source_image,
                    target_tenant_id=target_tenant_id,
                    target_product_id=int(target["id"]),
                    url=new_url,
                )
                scalar_updates["imagem_principal"] = new_url
                result.copied_images += 1
                _record_mapping(
                    db,
                    tenant_id=target_tenant_id,
                    user_id=user_id,
                    bundle_code=bundle_code,
                    bundle_version=bundle_version,
                    item_type="produto_imagem_ean",
                    source_id=int(source_image["id"]),
                    target_table="produto_imagens",
                    target_id=target_image_id,
                )
                has_updates = True

        updates = {**scalar_updates, **entity_updates}
        if dry_run:
            if has_updates or can_copy_image:
                result.would_update_products += 1
        elif updates:
            _update_target_product(
                db,
                target_tenant_id=target_tenant_id,
                target_product_id=int(target["id"]),
                updates=updates,
            )
            result.updated_products += 1
            _record_mapping(
                db,
                tenant_id=target_tenant_id,
                user_id=user_id,
                bundle_code=bundle_code,
                bundle_version=bundle_version,
                item_type="produto_ean",
                source_id=int(source["id"]),
                target_table="produtos",
                target_id=int(target["id"]),
            )

        sample_fields = set(updates)
        if can_copy_image:
            sample_fields.add("imagem_principal")
        if len(result.samples) < 20 and (has_updates or can_copy_image):
            result.samples.append(
                {
                    "gtin": gtin,
                    "source_product_id": int(source["id"]),
                    "target_product_id": int(target["id"]),
                    "source_name": source.get("nome"),
                    "target_name": target.get("nome"),
                    "fields": sorted(sample_fields),
                }
            )

    if dry_run:
        result.would_create = {
            table_name: len(keys)
            for table_name, keys in sorted(planned_entities.items())
        }
        result.would_create["produtos_enriquecidos"] = result.would_update_products
        result.would_create["produto_imagens"] = result.would_copy_images
    else:
        result.created = {
            **dict(result.entities_created),
            "produtos_enriquecidos": result.updated_products,
            "produto_imagens": result.copied_images,
        }
        result.skipped = {
            "produtos_sem_alteracao": result.matched_products - result.updated_products
        }
        _record_install(db, int(user_id), result)

    return result.to_dict()
