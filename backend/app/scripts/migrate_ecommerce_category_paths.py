"""Converte categorias legadas com ``>>`` em uma hierarquia real.

O modo padrão é apenas simulação. Nada é gravado sem ``--apply``.
"""

from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.db import SessionLocal
from app.models import Tenant
from app.produtos_models import Categoria, Produto
from app.tenancy.context import clear_current_tenant, set_current_tenant


def _parts(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(">>") if part.strip()]


def migrate_category_paths(*, tenant_ref: str, apply: bool = False) -> dict:
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_ref).first()
        if tenant is None:
            tenant = (
                db.query(Tenant)
                .filter(Tenant.ecommerce_slug == tenant_ref.strip().lower())
                .first()
            )
        if tenant is None:
            raise ValueError("Loja não encontrada pelo UUID ou slug informado.")

        tenant_uuid = UUID(str(tenant.id))
        set_current_tenant(tenant_uuid)
        categories = (
            db.query(Categoria)
            .filter(
                Categoria.tenant_id == tenant_uuid,
                Categoria.ativo.is_(True),
            )
            .order_by(Categoria.id.asc())
            .all()
        )
        legacy = [category for category in categories if len(_parts(category.nome)) > 1]
        cache = {
            (
                int(category.categoria_pai_id)
                if category.categoria_pai_id is not None
                else None,
                category.nome.strip().casefold(),
            ): category
            for category in categories
            if ">>" not in category.nome
        }

        created = 0
        reassigned_products = 0
        deactivated = 0
        plan = []

        for source in legacy:
            parent_id = None
            path = _parts(source.nome)
            target = None
            created_path = []
            for name in path:
                key = (parent_id, name.casefold())
                target = cache.get(key)
                if target is None:
                    target = Categoria(
                        tenant_id=tenant_uuid,
                        nome=name,
                        categoria_pai_id=parent_id,
                        departamento_id=source.departamento_id,
                        descricao=None,
                        icone=source.icone,
                        cor=source.cor,
                        ordem=source.ordem,
                        user_id=source.user_id,
                        ativo=True,
                    )
                    db.add(target)
                    db.flush()
                    cache[key] = target
                    created += 1
                    created_path.append(name)
                parent_id = target.id

            product_count = (
                db.query(Produto)
                .filter(
                    Produto.tenant_id == tenant_uuid,
                    Produto.categoria_id == source.id,
                )
                .update(
                    {Produto.categoria_id: target.id},
                    synchronize_session=False,
                )
            )
            reassigned_products += int(product_count or 0)
            source.ativo = False
            deactivated += 1
            plan.append(
                {
                    "origem_id": source.id,
                    "origem": source.nome,
                    "destino_id": target.id,
                    "destino": " > ".join(path),
                    "categorias_criadas": created_path,
                    "produtos_movidos": int(product_count or 0),
                }
            )

        result = {
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.ecommerce_slug,
            "modo": "aplicar" if apply else "simulacao",
            "categorias_legadas": len(legacy),
            "categorias_criadas": created,
            "categorias_legadas_desativadas": deactivated,
            "produtos_movidos": reassigned_products,
            "plano": plan,
        }
        if apply:
            db.commit()
        else:
            db.rollback()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        clear_current_tenant()
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Converte nomes Categoria >> Subcategoria em hierarquia real."
    )
    parser.add_argument("--tenant", required=True, help="UUID ou slug da loja")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava a conversão. Sem esta opção, executa somente uma simulação.",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            migrate_category_paths(tenant_ref=args.tenant, apply=args.apply),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
