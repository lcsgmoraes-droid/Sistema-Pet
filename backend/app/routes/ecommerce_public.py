import re
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Tenant
from app.produtos_models import Produto


router = APIRouter(prefix="/ecommerce", tags=["ecommerce-public"])
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _normalize_tenant_uuid(raw_tenant_id: str | None) -> str | None:
    if not raw_tenant_id:
        return None
    try:
        return str(UUID(str(raw_tenant_id).strip()))
    except Exception:
        return None


def _normalize_slug(raw_slug: str | None) -> str | None:
    if not raw_slug:
        return None
    slug = str(raw_slug).strip().lower()
    if not _SLUG_PATTERN.fullmatch(slug):
        return None
    return slug


def _resolve_tenant_ref(
    tenant: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    tenant_slug: str | None = Query(default=None),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
) -> tuple[str, str]:
    uuid_value = (
        _normalize_tenant_uuid(tenant_id)
        or _normalize_tenant_uuid(tenant)
        or _normalize_tenant_uuid(x_tenant_id)
    )
    if uuid_value:
        return ("id", uuid_value)

    slug_value = (
        _normalize_slug(tenant_slug)
        or _normalize_slug(tenant)
        or _normalize_slug(x_tenant_slug)
    )
    if slug_value:
        return ("slug", slug_value)

    if tenant_id or tenant_slug or tenant or x_tenant_id or x_tenant_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant inválido. Use UUID ou slug válido.",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="tenant obrigatório (UUID ou slug)",
    )


def _get_active_tenant(db: Session, tenant_ref: tuple[str, str]) -> Tenant:
    kind, value = tenant_ref

    if kind == "id":
        tenant = db.query(Tenant).filter(Tenant.id == value).first()
    else:
        tenant = db.query(Tenant).filter(func.lower(Tenant.ecommerce_slug) == value).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant não encontrado",
        )
    if str(tenant.status or "").lower() != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant inativo",
        )
    return tenant


@router.get("/tenant-context")
def tenant_context(
    tenant_ref: tuple[str, str] = Depends(_resolve_tenant_ref),
    db: Session = Depends(get_session),
):
    tenant = _get_active_tenant(db, tenant_ref)
    storefront_ref = tenant.ecommerce_slug or tenant.id
    return {
        "id": tenant.id,
        "name": tenant.name,
        "ecommerce_slug": tenant.ecommerce_slug,
        "storefront_path": f"/{storefront_ref}",
        "status": tenant.status,
        "cidade": tenant.cidade,
        "uf": tenant.uf,
    }


@router.get("/produtos")
def listar_produtos_publicos(
    tenant_ref: tuple[str, str] = Depends(_resolve_tenant_ref),
    busca: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_session),
):
    tenant = _get_active_tenant(db, tenant_ref)

    query = db.query(Produto).filter(
        Produto.tenant_id == tenant.id,
        Produto.ativo == True,
        Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
    )

    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(termo),
                Produto.codigo.ilike(termo),
                Produto.codigo_barras.ilike(termo),
            )
        )

    itens = query.order_by(Produto.nome.asc()).limit(limit).all()

    return {
        "items": [
            {
                "id": produto.id,
                "nome": produto.nome,
                "codigo": produto.codigo,
                "preco_venda": produto.preco_venda,
                "preco_promocional": produto.preco_promocional,
                "promocao_ativa": produto.promocao_ativa,
                "categoria_id": produto.categoria_id,
                "categoria_nome": getattr(produto.categoria, "nome", None),
                "estoque_ecommerce": produto.estoque_ecommerce,
                "estoque_atual": produto.estoque_atual,
                "imagem_principal": produto.imagem_principal,
            }
            for produto in itens
        ]
    }