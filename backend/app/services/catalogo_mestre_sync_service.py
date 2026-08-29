"""Sincronizacao unilateral de um tenant autorizado para o catalogo mestre.

Todas as consultas ao tenant de origem sao ``SELECT``. Os unicos INSERT/UPDATE
deste modulo apontam para tabelas com prefixo ``catalogo_mestre_``.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.services.catalogo_mestre_core import (
    DEFAULT_IMAGE_TARGET,
    CatalogoMestreError,
    CatalogoMestreSyncResult,
    build_source_payload,
    json_safe,
    pending_specs,
    quality_and_gaps,
    refresh_source_snapshot,
    source_image_urls,
    utcnow,
)
from app.tenancy.rls import sync_rls_tenant

MASTER_TABLES = (
    "catalogo_mestre_produtos",
    "catalogo_mestre_imagens",
    "catalogo_mestre_pendencias",
    "catalogo_mestre_sincronizacoes",
)
SOURCE_TABLES = {
    "produtos",
    "produto_imagens",
    "produto_config_fiscal",
    "marcas",
    "categorias",
    "departamentos",
}
JSON_FIELDS = {
    "codigos_barras",
    "tags",
    "dados_fiscais_referencia",
    "dados_fisicos",
    "dados_racao",
    "especies_indicadas",
    "bula_conteudo",
    "posologia",
    "lacunas",
    "gaps",
    "proveniencia",
    "snapshot_origem",
    "metadados",
    "detalhes",
    "resumo",
}
SOURCE_OWNED_FIELDS = {
    "fonte_primaria",
    "origem_atualizado_em",
    "codigo_origem",
    "nome",
    "tipo_catalogo",
    "gtin",
    "gtin_status",
    "codigos_barras",
    "marca",
    "categoria",
    "departamento",
    "subcategoria",
    "descricao_curta",
    "descricao_completa",
    "tags",
    "unidade",
    "ncm",
    "cest",
    "origem_mercadoria",
    "dados_fiscais_referencia",
    "dados_fisicos",
    "dados_racao",
    "registro_mapa",
    "principio_ativo",
    "fabricante",
    "forma_farmaceutica",
    "especies_indicadas",
    "bula_url",
    "bula_conteudo",
    "posologia",
    "conteudo_veterinario_status",
}


def _table_exists(db: Session, table_name: str) -> bool:
    return inspect(db.connection()).has_table(table_name)


def _decode_json(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return default
    return default


def _json_bind(value: Any, dialect_name: str) -> Any:
    safe_value = json_safe(value)
    if dialect_name == "postgresql":
        try:
            from psycopg2.extras import Json

            return Json(safe_value)
        except ImportError:
            return json.dumps(safe_value, ensure_ascii=False, sort_keys=True)
    return json.dumps(safe_value, ensure_ascii=False, sort_keys=True)


def _bind_values(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    dialect_name = db.get_bind().dialect.name
    return {
        key: _json_bind(value, dialect_name) if key in JSON_FIELDS else value
        for key, value in values.items()
    }


def _source_rows(db: Session, table_name: str, source_tenant_id: str) -> list[dict]:
    if table_name not in SOURCE_TABLES:
        raise CatalogoMestreError(f"Tabela fonte nao permitida: {table_name}.")
    if not _table_exists(db, table_name):
        return []
    sync_rls_tenant(db, source_tenant_id)
    rows = db.execute(
        text(
            f"SELECT * FROM {table_name} "
            "WHERE CAST(tenant_id AS TEXT) = :source_tenant_id ORDER BY id"
        ),
        {"source_tenant_id": source_tenant_id},
    ).mappings()
    return [dict(row) for row in rows]


def _is_false(value: Any) -> bool:
    return (
        value is False
        or value == 0
        or str(value).strip().casefold()
        in {
            "false",
            "f",
            "nao",
            "não",
        }
    )


def _eligible_product(product: dict[str, Any]) -> bool:
    if product.get("deleted_at") not in (None, ""):
        return False
    for flag in ("situacao", "ativo", "is_sellable"):
        if flag in product and _is_false(product.get(flag)):
            return False
    product_type = str(product.get("tipo") or "produto").strip().casefold()
    if product_type in {"servico", "serviço"}:
        return False
    structured_type = str(product.get("tipo_produto") or "").strip().upper()
    return structured_type != "PAI"


def _name_map(rows: list[dict[str, Any]]) -> dict[int, str]:
    return {
        int(row["id"]): str(row.get("nome") or "").strip()
        for row in rows
        if row.get("id") is not None and str(row.get("nome") or "").strip()
    }


def _master_rows(db: Session, table_name: str) -> list[dict[str, Any]]:
    if not _table_exists(db, table_name):
        return []
    return [
        dict(row) for row in db.execute(text(f"SELECT * FROM {table_name}")).mappings()
    ]


def _same_source(owner: Any, source_tenant_id: str, source_product_id: int) -> bool:
    if not isinstance(owner, dict):
        return False
    return (
        owner.get("tipo") == "tenant_produto"
        and str(owner.get("source_tenant_id")) == source_tenant_id
        and int(owner.get("source_product_id") or 0) == source_product_id
    )


def _merge_source_payload(
    existing: dict[str, Any], incoming: dict[str, Any]
) -> dict[str, Any]:
    """Atualiza apenas campos ainda pertencentes a esta mesma fonte."""

    source_tenant_id = str(incoming["origem_tenant_id"])
    source_product_id = int(incoming["origem_produto_id"])
    existing_provenance = _decode_json(existing.get("proveniencia"), {}) or {}
    existing_owners = existing_provenance.get("campos") or {}
    incoming_provenance = incoming["proveniencia"]
    incoming_owners = incoming_provenance.get("campos") or {}

    merged = dict(existing)
    for field_name in SOURCE_OWNED_FIELDS:
        owner = existing_owners.get(field_name)
        if owner is None or _same_source(owner, source_tenant_id, source_product_id):
            merged[field_name] = incoming.get(field_name)
            if field_name in incoming_owners:
                existing_owners[field_name] = incoming_owners[field_name]

    existing_provenance["fonte_primaria"] = incoming_provenance["fonte_primaria"]
    existing_provenance["campos"] = existing_owners
    merged.update(
        {
            "origem_atualizado_em": incoming.get("origem_atualizado_em"),
            "imagem_meta_quantidade": incoming["imagem_meta_quantidade"],
            "proveniencia": existing_provenance,
            "snapshot_origem": incoming["snapshot_origem"],
            "snapshot_origem_hash": incoming["snapshot_origem_hash"],
            "ultima_sincronizacao_em": incoming["ultima_sincronizacao_em"],
        }
    )
    return merged


def _insert_product(db: Session, payload: dict[str, Any]) -> int:
    values = {
        key: value
        for key, value in payload.items()
        if key not in {"id", "created_at", "updated_at"}
    }
    columns = ", ".join(values)
    params = ", ".join(f":{key}" for key in values)
    return int(
        db.execute(
            text(
                f"INSERT INTO catalogo_mestre_produtos ({columns}) "
                f"VALUES ({params}) RETURNING id"
            ),
            _bind_values(db, values),
        ).scalar_one()
    )


def _update_product(db: Session, product_id: int, payload: dict[str, Any]) -> None:
    values = {
        key: value
        for key, value in payload.items()
        if key
        not in {
            "id",
            "created_at",
            "updated_at",
            "origem_tenant_id",
            "origem_produto_id",
        }
    }
    values["updated_at"] = utcnow()
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    bound = _bind_values(db, values)
    bound["product_id"] = product_id
    db.execute(
        text(
            f"UPDATE catalogo_mestre_produtos SET {assignments} WHERE id = :product_id"
        ),
        bound,
    )


def _insert_sync_run(
    db: Session,
    source_tenant_id: str,
    source_identifier: str | None,
    image_target: int,
) -> int:
    return int(
        db.execute(
            text("""
                INSERT INTO catalogo_mestre_sincronizacoes (
                    origem_tenant_id, origem_identificador, modo, status,
                    imagem_meta_quantidade, iniciada_em
                ) VALUES (
                    :source_tenant_id, :source_identifier, 'apply', 'executando',
                    :image_target, :now
                ) RETURNING id
                """),
            {
                "source_tenant_id": source_tenant_id,
                "source_identifier": source_identifier,
                "image_target": image_target,
                "now": utcnow(),
            },
        ).scalar_one()
    )


def _validate_request(
    db: Session, source_tenant_id: str, image_target: int, dry_run: bool
) -> None:
    if not source_tenant_id:
        raise CatalogoMestreError("Tenant de origem e obrigatorio.")
    if image_target < 1 or image_target > 12:
        raise CatalogoMestreError("A meta de imagens deve ficar entre 1 e 12.")
    if not _table_exists(db, "produtos"):
        raise CatalogoMestreError("Tabela fonte produtos nao encontrada.")
    missing = [table for table in MASTER_TABLES if not _table_exists(db, table)]
    if missing and not dry_run:
        raise CatalogoMestreError(
            "Schema do catalogo mestre ainda nao foi aplicado: " + ", ".join(missing)
        )


def sync_catalogo_mestre_from_tenant(
    *,
    db: Session,
    source_tenant_id: str,
    source_identifier: str | None = None,
    dry_run: bool = True,
    image_target: int = DEFAULT_IMAGE_TARGET,
    sample_limit: int = 20,
) -> dict[str, Any]:
    """Monta ou atualiza o catalogo mestre sem escrever no tenant de origem."""

    source_tenant_id = str(source_tenant_id or "").strip()
    _validate_request(db, source_tenant_id, image_target, dry_run)
    result = CatalogoMestreSyncResult(
        source_tenant_id=source_tenant_id,
        dry_run=dry_run,
        image_target=image_target,
    )
    synced_at = utcnow()

    products = _source_rows(db, "produtos", source_tenant_id)
    result.source_products = len(products)
    eligible = [product for product in products if _eligible_product(product)]
    result.eligible_products = len(eligible)
    result.skipped_products = len(products) - len(eligible)

    brands = _name_map(_source_rows(db, "marcas", source_tenant_id))
    categories = _name_map(_source_rows(db, "categorias", source_tenant_id))
    departments = _name_map(_source_rows(db, "departamentos", source_tenant_id))
    fiscal_by_product = {
        int(row["produto_id"]): row
        for row in _source_rows(db, "produto_config_fiscal", source_tenant_id)
        if row.get("produto_id") is not None
    }
    images_by_product: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in _source_rows(db, "produto_imagens", source_tenant_id):
        if row.get("produto_id") is not None:
            images_by_product[int(row["produto_id"])].append(row)

    payloads: dict[int, dict[str, Any]] = {}
    source_images: dict[int, list[dict[str, Any]]] = {}
    for product in eligible:
        product_id = int(product["id"])
        payload = build_source_payload(
            product=product,
            source_tenant_id=source_tenant_id,
            brand=brands.get(int(product.get("marca_id") or 0)),
            category=categories.get(int(product.get("categoria_id") or 0)),
            department=departments.get(int(product.get("departamento_id") or 0)),
            fiscal=fiscal_by_product.get(product_id),
            image_target=image_target,
            synced_at=synced_at,
        )
        payloads[product_id] = payload
        source_images[product_id] = source_image_urls(
            product, images_by_product.get(product_id, [])
        )

    gtin_counts = Counter(
        payload["gtin"] for payload in payloads.values() if payload.get("gtin")
    )
    duplicate_codes = {gtin for gtin, count in gtin_counts.items() if count > 1}
    for payload in payloads.values():
        if payload.get("gtin") in duplicate_codes:
            payload["gtin_status"] = "duplicado_origem"
            refresh_source_snapshot(payload)
        if payload["gtin_status"] == "valido":
            result.valid_gtins += 1
        elif payload["gtin_status"] == "duplicado_origem":
            result.duplicate_gtins += 1
        elif payload["gtin_status"] == "invalido":
            result.invalid_gtins += 1
        else:
            result.missing_gtins += 1
        result.bump("types", payload["tipo_catalogo"])
    if duplicate_codes:
        result.warnings.append(
            f"{len(duplicate_codes)} GTINs aparecem em mais de um produto da origem; "
            "foram mantidos para revisao, sem fusao automatica."
        )

    existing_products = {
        int(row["origem_produto_id"]): row
        for row in _master_rows(db, "catalogo_mestre_produtos")
        if str(row.get("origem_tenant_id")) == source_tenant_id
    }
    existing_images = _master_rows(db, "catalogo_mestre_imagens")
    image_rows_by_master: dict[int, list[dict[str, Any]]] = defaultdict(list)
    image_by_source_url: dict[tuple[int, str], dict[str, Any]] = {}
    for row in existing_images:
        master_id = int(row["produto_id"])
        image_rows_by_master[master_id].append(row)
        if row.get("url_origem"):
            image_by_source_url[(master_id, str(row["url_origem"]))] = row

    master_id_by_source: dict[int, int | None] = {}
    merged_by_source: dict[int, dict[str, Any]] = {}
    sync_run_id = None
    if not dry_run:
        sync_run_id = _insert_sync_run(
            db, source_tenant_id, source_identifier, image_target
        )

    for source_product_id, payload in payloads.items():
        existing = existing_products.get(source_product_id)
        if existing is None:
            result.would_create_products += int(dry_run)
            if dry_run:
                master_id = None
                merged = payload
            else:
                master_id = _insert_product(db, payload)
                result.created_products += 1
                merged = payload
        else:
            master_id = int(existing["id"])
            changed = (
                existing.get("snapshot_origem_hash") != payload["snapshot_origem_hash"]
            )
            merged = _merge_source_payload(existing, payload)
            if changed:
                if dry_run:
                    result.would_update_products += 1
                else:
                    _update_product(db, master_id, merged)
                    result.updated_products += 1
            else:
                result.unchanged_products += 1
                if not dry_run:
                    db.execute(
                        text(
                            "UPDATE catalogo_mestre_produtos "
                            "SET ultima_sincronizacao_em=:now WHERE id=:product_id"
                        ),
                        {"now": synced_at, "product_id": master_id},
                    )
        master_id_by_source[source_product_id] = master_id
        merged_by_source[source_product_id] = merged

    image_inserts: list[dict[str, Any]] = []
    image_reactivations: list[dict[str, Any]] = []
    for source_product_id, rows in source_images.items():
        master_id = master_id_by_source[source_product_id]
        result.source_images += len(rows)
        for image_data in rows:
            url = image_data["url"]
            existing_image = (
                image_by_source_url.get((int(master_id), url))
                if master_id is not None
                else None
            )
            if existing_image is not None:
                if _is_false(existing_image.get("ativo")) and not dry_run:
                    image_reactivations.append({"id": existing_image["id"]})
                continue
            if dry_run:
                result.would_import_images += 1
                continue
            image_inserts.append(
                _bind_values(
                    db,
                    {
                        "produto_id": int(master_id),
                        "tipo_origem": "tenant_produto",
                        "url_origem": url,
                        "arquivo_url": url,
                        "ordem": image_data["ordem"],
                        "e_principal": image_data["e_principal"],
                        "gerada_por_ia": False,
                        "direitos_uso_status": "nao_verificado",
                        "status_revisao": "pendente",
                        "largura": image_data["largura"],
                        "altura": image_data["altura"],
                        "tamanho_bytes": image_data["tamanho_bytes"],
                        "metadados": {
                            "source_tenant_id": source_tenant_id,
                            "source_product_id": source_product_id,
                            "source_product_image_id": image_data["produto_imagem_id"],
                        },
                        "ativo": True,
                        "created_at": synced_at,
                        "updated_at": synced_at,
                    },
                )
            )
    if image_inserts:
        db.execute(
            text("""
                INSERT INTO catalogo_mestre_imagens (
                    produto_id, tipo_origem, url_origem, arquivo_url, ordem,
                    e_principal, gerada_por_ia, direitos_uso_status, status_revisao,
                    largura, altura, tamanho_bytes, metadados, ativo, created_at, updated_at
                ) VALUES (
                    :produto_id, :tipo_origem, :url_origem, :arquivo_url, :ordem,
                    :e_principal, :gerada_por_ia, :direitos_uso_status, :status_revisao,
                    :largura, :altura, :tamanho_bytes, :metadados, :ativo, :created_at, :updated_at
                )
                """),
            image_inserts,
        )
        result.imported_images += len(image_inserts)
    if image_reactivations:
        db.execute(
            text(
                "UPDATE catalogo_mestre_imagens "
                "SET ativo=true, updated_at=:updated_at WHERE id=:id"
            ),
            [dict(item, updated_at=synced_at) for item in image_reactivations],
        )

    existing_pending_rows = _master_rows(db, "catalogo_mestre_pendencias")
    pending_by_key = {
        (int(row["produto_id"]), str(row["tipo"]), int(row["posicao_alvo"])): row
        for row in existing_pending_rows
    }
    desired_keys: set[tuple[int, str, int]] = set()
    pending_inserts: list[dict[str, Any]] = []
    reopen_updates: list[dict[str, Any]] = []
    quality_total = 0.0

    for source_product_id, payload in merged_by_source.items():
        master_id = master_id_by_source[source_product_id]
        existing_urls: set[str] = set()
        if master_id is not None:
            for row in image_rows_by_master.get(int(master_id), []):
                if not _is_false(row.get("ativo")):
                    url = row.get("arquivo_url") or row.get("url_origem")
                    if url:
                        existing_urls.add(str(url))
        existing_urls.update(image["url"] for image in source_images[source_product_id])
        image_count = len(existing_urls)
        missing_images = max(image_target - image_count, 0)
        quality, gaps = quality_and_gaps(payload, image_count, image_target)
        quality_total += quality
        if missing_images:
            result.products_below_image_target += 1
            result.image_slots_missing += missing_images

        payload.update(
            {
                "imagem_quantidade": image_count,
                "imagem_meta_quantidade": image_target,
                "imagem_faltantes": missing_images,
                "qualidade_percentual": quality,
                "lacunas": gaps,
            }
        )
        if not dry_run:
            db.execute(
                text("""
                    UPDATE catalogo_mestre_produtos
                       SET imagem_quantidade=:image_count,
                           imagem_meta_quantidade=:image_target,
                           imagem_faltantes=:missing_images,
                           qualidade_percentual=:quality,
                           lacunas=:gaps,
                           updated_at=:updated_at
                     WHERE id=:product_id
                    """),
                _bind_values(
                    db,
                    {
                        "image_count": image_count,
                        "image_target": image_target,
                        "missing_images": missing_images,
                        "quality": quality,
                        "gaps": gaps,
                        "updated_at": synced_at,
                        "product_id": int(master_id),
                    },
                ),
            )

        specs = pending_specs(payload, image_count, image_target)
        for spec in specs:
            result.bump("pending_types", spec.tipo)
            if master_id is None:
                result.would_create_pending_tasks += 1
                continue
            key = (int(master_id), spec.tipo, spec.posicao_alvo)
            desired_keys.add(key)
            existing_pending = pending_by_key.get(key)
            if existing_pending is None:
                if dry_run:
                    result.would_create_pending_tasks += 1
                else:
                    pending_inserts.append(
                        _bind_values(
                            db,
                            {
                                "produto_id": int(master_id),
                                "tipo": spec.tipo,
                                "posicao_alvo": spec.posicao_alvo,
                                "status": "pendente",
                                "prioridade": spec.prioridade,
                                "origem_preferida": spec.origem_preferida,
                                "detalhes": spec.detalhes or None,
                                "tentativas": 0,
                                "created_at": synced_at,
                                "updated_at": synced_at,
                            },
                        )
                    )
            elif str(existing_pending.get("status")) in {"resolvida", "cancelada"}:
                if dry_run:
                    result.would_create_pending_tasks += 1
                else:
                    reopen_updates.append(
                        {
                            "id": existing_pending["id"],
                            "status": "pendente",
                            "updated_at": synced_at,
                        }
                    )

        if len(result.samples) < sample_limit:
            result.samples.append(
                {
                    "source_product_id": source_product_id,
                    "name": payload["nome"],
                    "type": payload["tipo_catalogo"],
                    "gtin": payload.get("gtin"),
                    "gtin_status": payload["gtin_status"],
                    "images": image_count,
                    "missing_images": missing_images,
                    "quality": quality,
                }
            )

    if pending_inserts:
        db.execute(
            text("""
                INSERT INTO catalogo_mestre_pendencias (
                    produto_id, tipo, posicao_alvo, status, prioridade,
                    origem_preferida, detalhes, tentativas, created_at, updated_at
                ) VALUES (
                    :produto_id, :tipo, :posicao_alvo, :status, :prioridade,
                    :origem_preferida, :detalhes, :tentativas, :created_at, :updated_at
                )
                """),
            pending_inserts,
        )
        result.created_pending_tasks += len(pending_inserts)
    if reopen_updates:
        db.execute(
            text(
                "UPDATE catalogo_mestre_pendencias "
                "SET status=:status, resolvida_em=NULL, updated_at=:updated_at WHERE id=:id"
            ),
            reopen_updates,
        )
        result.created_pending_tasks += len(reopen_updates)

    if not dry_run:
        scoped_master_ids = {
            int(master_id)
            for master_id in master_id_by_source.values()
            if master_id is not None
        }
        resolve_updates = []
        for key, row in pending_by_key.items():
            if (
                key[0] in scoped_master_ids
                and key not in desired_keys
                and str(row.get("status")) == "pendente"
            ):
                resolve_updates.append({"id": row["id"], "resolved_at": synced_at})
        if resolve_updates:
            db.execute(
                text("""
                    UPDATE catalogo_mestre_pendencias
                       SET status='resolvida', resolvida_em=:resolved_at,
                           updated_at=:resolved_at
                     WHERE id=:id
                    """),
                resolve_updates,
            )
            result.resolved_pending_tasks += len(resolve_updates)

    if payloads:
        result.quality_average = round(quality_total / len(payloads), 2)
    if result.products_below_image_target:
        result.warnings.append(
            f"{result.products_below_image_target} produtos ainda estao abaixo da meta "
            f"de {image_target} imagens."
        )

    response = result.to_dict()
    if sync_run_id is not None:
        db.execute(
            text("""
                UPDATE catalogo_mestre_sincronizacoes
                   SET status='concluida', resumo=:summary, concluida_em=:finished_at
                 WHERE id=:sync_run_id
                """),
            {
                "summary": _json_bind(response, db.get_bind().dialect.name),
                "finished_at": utcnow(),
                "sync_run_id": sync_run_id,
            },
        )
    return response
