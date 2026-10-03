"""Associa imagens verificadas do catalogo padrao aos produtos JN importados.

Executar depois da carga JN. O plano nao altera dados nem copia arquivos; a
aplicacao exige o mesmo catalogo, banco e tenant vistos na simulacao.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

import app.db.base  # noqa: F401 - registra modelos relacionados
from app.db import SessionLocal
from app.models import Tenant
from app.produtos_catalogo_models import Produto
from app.produtos_estoque_models import ProdutoImagem
from app.services.base_catalog_import_images import copy_product_image_url
from app.services.product_image_storage import (
    get_product_image_storage_backend,
    is_s3_product_image_url,
)
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant
from importar_jnm_catalogo import JnmImportError
from importar_jnm_catalogo_cli import _material_hash, _target, _write_json
from importar_simplesvet_plan import database_identity, environment_name, is_production


REFERENCE_TENANT_ID = "180d9cbf-5dcb-4676-bf11-dcbd91ed444b"
EXPECTED_TARGET_PRODUCTS = 2625
IMAGE_PREFIX = "https://img.corepet.com.br/produtos/"
PLAN_LIFETIME = timedelta(hours=24)


def name_signature(name: str) -> tuple[str, ...]:
    folded = unicodedata.normalize("NFKD", name.upper())
    plain = "".join(ch for ch in folded if not unicodedata.combining(ch))
    plain = re.sub(r"(\d+)\s+(KG|G|ML|L)\b", r"\1\2", plain)
    plain = re.sub(r"[^A-Z0-9]+", " ", plain)
    substitutions = {
        "RAC": "RACAO",
        "AREI": "AREIA",
        "ADULTOS": "ADULTO",
        "FILHOTES": "FILHOTE",
        "CAES": "CAO",
        "GATOS": "GATO",
        "UNI": "UNIDADE",
        "UNIDADES": "UNIDADE",
    }
    stop = {"DE", "DA", "DO", "DAS", "DOS", "PARA"}
    return tuple(
        sorted(
            substitutions.get(part, part) for part in plain.split() if part not in stop
        )
    )


def unique_image_matches(targets: list[dict], references: list[dict]) -> list[dict]:
    by_signature: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    target_counts = Counter(name_signature(row["nome"]) for row in targets)
    for row in references:
        expected_prefix = f"{IMAGE_PREFIX}{REFERENCE_TENANT_ID}/{row['id']}/originais/"
        if str(row.get("imagem_principal") or "").startswith(expected_prefix):
            by_signature[name_signature(row["nome"])].append(row)
    matches = []
    for row in targets:
        signature = name_signature(row["nome"])
        donors = by_signature.get(signature, [])
        if (
            row["tipo"] != "produto"
            or target_counts[signature] != 1
            or len(donors) != 1
        ):
            continue
        donor = donors[0]
        matches.append(
            {
                "target_id": row["id"],
                "target_codigo": row["codigo"],
                "target_name": row["nome"],
                "reference_id": donor["id"],
                "reference_name": donor["nome"],
                "reference_url": donor["imagem_principal"],
                "method": "unique_exact_normalized_name",
            }
        )
    return sorted(matches, key=lambda item: item["target_id"])


def _rows(db, tenant_id: str) -> list[dict]:
    with tenant_context(tenant_id):
        sync_rls_tenant(db, tenant_id)
        rows = db.execute(
            select(
                Produto.id,
                Produto.codigo,
                Produto.nome,
                Produto.tipo,
                Produto.imagem_principal,
            ).where(Produto.tenant_id == UUID(tenant_id))
        ).all()
    return [dict(row._mapping) for row in rows]


def _snapshot(db, tenant_id: str, user_id: int, expected_cnpj: str) -> dict:
    target = _target(db, tenant_id, user_id, expected_cnpj)
    with tenant_context(REFERENCE_TENANT_ID):
        sync_rls_tenant(db, REFERENCE_TENANT_ID)
        if not db.get(Tenant, REFERENCE_TENANT_ID):
            raise JnmImportError("Tenant do catalogo padrao ausente")
    reference_rows = _rows(db, REFERENCE_TENANT_ID)
    target_rows = _rows(db, tenant_id)
    if len(target_rows) != EXPECTED_TARGET_PRODUCTS:
        raise JnmImportError("Quantidade de produtos JN no destino divergente")
    if any(row["imagem_principal"] for row in target_rows):
        raise JnmImportError("Destino ja possui imagem principal de produto")
    if get_product_image_storage_backend() != "s3":
        raise JnmImportError("Armazenamento S3 de imagens nao esta ativo")
    matches = unique_image_matches(target_rows, reference_rows)
    if not matches or any(
        not is_s3_product_image_url(match["reference_url"]) for match in matches
    ):
        raise JnmImportError("Nenhuma imagem confiavel ou URL fora do S3 configurado")
    return {
        "target": target,
        "reference_tenant_id": REFERENCE_TENANT_ID,
        "reference_products": len(reference_rows),
        "target_products": len(target_rows),
        "matches": matches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--tenant-id", required=True)
    plan.add_argument("--user-id", required=True, type=int)
    plan.add_argument("--expected-target-cnpj", required=True)
    plan.add_argument(
        "--report-dir", type=Path, default=Path("data/importacoes-jnm/reports")
    )
    apply = commands.add_parser("apply")
    apply.add_argument("--plan-file", required=True, type=Path)
    apply.add_argument("--confirm-tenant-id", required=True)
    apply.add_argument("--confirm-plan-id", required=True)
    apply.add_argument("--allow-production-apply", action="store_true")
    apply.add_argument("--confirm-production")
    args = parser.parse_args()
    try:
        if args.command == "plan":
            tenant_id = str(UUID(args.tenant_id))
            with SessionLocal() as db:
                database = database_identity(str(db.get_bind().url))
                snapshot = _snapshot(
                    db, tenant_id, args.user_id, args.expected_target_cnpj
                )
                db.rollback()
            now = datetime.now(timezone.utc)
            payload = {
                "version": 1,
                "status": "simulation_complete",
                "created_at": now.isoformat(),
                "expires_at": (now + PLAN_LIFETIME).isoformat(),
                "environment": environment_name(),
                "database": database,
                **snapshot,
            }
            payload["plan_id"] = _material_hash(payload)
            path = (
                args.report_dir.resolve()
                / f"jnm-images-plan-{payload['plan_id'][:16]}.json"
            )
            _write_json(path, payload)
            result = {
                "ok": True,
                "mode": "plan",
                "plan_id": payload["plan_id"],
                "plan_file": str(path),
                "matches": len(snapshot["matches"]),
                "changes_saved": False,
            }
        else:
            payload = json.loads(args.plan_file.read_text(encoding="utf-8"))
            if (
                payload.get("version") != 1
                or payload.get("status") != "simulation_complete"
                or payload.get("plan_id") != _material_hash(payload)
                or payload["plan_id"] != args.confirm_plan_id
            ):
                raise JnmImportError("Plano de imagens invalido")
            tenant_id = str(UUID(args.confirm_tenant_id))
            if tenant_id != payload["target"]["tenant_id"]:
                raise JnmImportError("Tenant confirmado difere do plano")
            if datetime.now(timezone.utc) > datetime.fromisoformat(
                payload["expires_at"]
            ):
                raise JnmImportError("Plano expirado")
            with SessionLocal() as db:
                database = database_identity(str(db.get_bind().url))
                if database != payload["database"]:
                    raise JnmImportError("Banco difere do plano")
                if is_production(environment_name(), database) and (
                    not args.allow_production_apply
                    or args.confirm_production != f"IMPORTAR-JNM-IMAGENS-{tenant_id}"
                ):
                    raise JnmImportError(
                        "Aplicacao de imagens em producao exige confirmacao"
                    )
                snapshot = _snapshot(
                    db,
                    tenant_id,
                    payload["target"]["user_id"],
                    payload["target"]["tenant_cnpj"],
                )
                if any(snapshot[key] != payload[key] for key in snapshot):
                    raise JnmImportError("Catalogo ou imagens mudaram desde o plano")
                with tenant_context(tenant_id):
                    sync_rls_tenant(db, tenant_id)
                    for match in snapshot["matches"]:
                        new_url = copy_product_image_url(
                            match["reference_url"],
                            source_tenant_id=REFERENCE_TENANT_ID,
                            source_product_id=match["reference_id"],
                            target_tenant_id=tenant_id,
                            target_product_id=match["target_id"],
                        )
                        if new_url == match["reference_url"] or len(new_url) > 255:
                            raise JnmImportError(
                                "Imagem copiada sem URL exclusiva valida"
                            )
                        db.add(
                            ProdutoImagem(
                                tenant_id=UUID(tenant_id),
                                produto_id=match["target_id"],
                                url=new_url,
                                ordem=0,
                                e_principal=True,
                            )
                        )
                        db.execute(
                            Produto.__table__.update()
                            .where(
                                Produto.id == match["target_id"],
                                Produto.tenant_id == UUID(tenant_id),
                            )
                            .values(imagem_principal=new_url)
                        )
                    db.commit()
                result = {
                    "ok": True,
                    "mode": "apply",
                    "tenant_id": tenant_id,
                    "images_associated": len(snapshot["matches"]),
                }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (JnmImportError, ValueError, KeyError, OSError) as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1
    except Exception:
        print(
            "Falha ao associar imagens; transacao do banco revertida.", file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
