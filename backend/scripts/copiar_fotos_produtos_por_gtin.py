"""Copia somente fotos de produtos existentes por GTIN valido.

Simula por padrao. A aplicacao exige contagens esperadas e confirmacao do
tenant destino, inclusive quando executada em producao.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

if Path("/app/app").is_dir() and "/app" not in sys.path:
    sys.path.insert(0, "/app")

from app.db import SessionLocal  # noqa: E402
from app.services.base_catalog_image_copy_service import (  # noqa: E402
    copy_missing_images_by_gtin,
)
from app.tenancy.context import tenant_context  # noqa: E402
from app.tenancy.rls import sync_rls_tenant  # noqa: E402


def _uuid(value: str) -> str:
    return str(UUID(value))


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source-tenant-id", action="append", required=True, type=_uuid)
    cli.add_argument("--target-tenant-id", required=True, type=_uuid)
    cli.add_argument("--actor-user-id", required=True, type=int)
    cli.add_argument("--apply", action="store_true")
    cli.add_argument("--expected-products", type=int)
    cli.add_argument("--expected-images", type=int)
    cli.add_argument("--confirm")
    return cli


def _verify_actor(db, tenant_id: str, user_id: int) -> None:
    with tenant_context(tenant_id):
        sync_rls_tenant(db, tenant_id)
        found = db.execute(
            text("""
                SELECT 1 FROM users
                 WHERE CAST(tenant_id AS TEXT)=:tenant_id
                   AND id=:user_id AND is_active IS TRUE
                 LIMIT 1
            """),
            {"tenant_id": tenant_id, "user_id": user_id},
        ).scalar()
    if not found:
        raise ValueError("Usuario ativo nao pertence ao tenant destino.")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.actor_user_id <= 0:
        parser().error("--actor-user-id precisa ser positivo")
    if args.apply:
        expected_confirm = f"COPIAR-FOTOS-{args.target_tenant_id}"
        if args.confirm != expected_confirm:
            parser().error(f"Aplicacao exige --confirm {expected_confirm}")
        if args.expected_products is None or args.expected_images is None:
            parser().error("Aplicacao exige as contagens da simulacao.")

    db = SessionLocal()
    try:
        _verify_actor(db, args.target_tenant_id, args.actor_user_id)
        simulation = copy_missing_images_by_gtin(
            db=db,
            source_tenant_ids=args.source_tenant_id,
            target_tenant_id=args.target_tenant_id,
            user_id=args.actor_user_id,
            dry_run=True,
        )
        if not args.apply:
            db.rollback()
            print(json.dumps(simulation, ensure_ascii=False, indent=2, sort_keys=True))
            return 0

        if (
            simulation["candidate_products"] != args.expected_products
            or simulation["candidate_images"] != args.expected_images
        ):
            raise ValueError(
                "Candidatos mudaram desde a simulacao; revise antes de aplicar."
            )
        applied = copy_missing_images_by_gtin(
            db=db,
            source_tenant_ids=args.source_tenant_id,
            target_tenant_id=args.target_tenant_id,
            user_id=args.actor_user_id,
            dry_run=False,
        )
        if (
            applied["copied_products"] != args.expected_products
            or applied["copied_images"] != args.expected_images
        ):
            raise ValueError(
                "Resultado nao coincide com a simulacao; transacao desfeita."
            )
        db.commit()
        print(json.dumps(applied, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        db.rollback()
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
