import re
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db import get_session
from app.models import Tenant
from app.produtos_models import Produto
from app.services.validade_campanha_service import (
    mapear_ofertas_validade_por_produto,
    resolver_preco_publico_produto,
)


router = APIRouter(prefix="/ecommerce", tags=["ecommerce-public"])
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CATALOG_ORDER_OPTIONS = {"prontos", "nome", "menor_preco", "maior_preco"}


def _serializar_promocao_validade(oferta, origem_preco: str | None) -> dict | None:
    if not oferta:
        return None
    return {
        "ativa": bool(oferta.active),
        "origem_preco_promocional": origem_preco,
        "lote_id": oferta.lote_id,
        "nome_lote": oferta.lote_nome,
        "dias_para_vencer": oferta.dias_para_vencer,
        "quantidade_promocional": oferta.quantity_available,
        "percentual_desconto": oferta.percentual_desconto,
        "preco_promocional": oferta.promotional_price,
        "faixa": oferta.faixa,
        "label": oferta.label,
        "mensagem": oferta.message,
    }


def _normalize_sales_channel(raw_channel: str | None) -> str:
    value = str(raw_channel or "ecommerce").strip().lower()
    if value in {"app", "app_movel", "mobile", "aplicativo"}:
        return "app"
    return "ecommerce"


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


@router.get("/tenant-slug/{slug}")
def buscar_tenant_por_slug(
    slug: str,
    db: Session = Depends(get_session),
):
    """
    Descobre um tenant pelo slug.
    Usado pelo app mobile para vincular o app a uma loja.
    Retorna informações básicas da loja (nome, logo).
    """
    slug_norm = _normalize_slug(slug)
    if not slug_norm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug inválido. Use apenas letras minúsculas, números e hífens.",
        )

    tenant = db.query(Tenant).filter(
        func.lower(Tenant.ecommerce_slug) == slug_norm
    ).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loja não encontrada. Verifique o código e tente novamente.",
        )
    if str(tenant.status or "").lower() != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta loja não está ativa no momento.",
        )

    return {
        "id": str(tenant.id),
        "slug": tenant.ecommerce_slug,
        "nome": tenant.name,
        "logo_url": tenant.logo_url,
        "cidade": tenant.cidade,
        "uf": tenant.uf,
    }


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
        "logo_url": tenant.logo_url,
        "banner_1_url": tenant.banner_1_url,
        "banner_2_url": tenant.banner_2_url,
        "banner_3_url": tenant.banner_3_url,
    }


@router.get("/produtos")
def listar_produtos_publicos(
    tenant_ref: tuple[str, str] = Depends(_resolve_tenant_ref),
    busca: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    apenas_com_estoque: bool = Query(default=False),
    apenas_com_imagem: bool = Query(default=False),
    ordenacao: str = Query(default="prontos"),
    canal: str | None = Query(default=None),
    x_canal_venda: str | None = Header(default=None, alias="X-Canal-Venda"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_session),
):
    tenant = _get_active_tenant(db, tenant_ref)
    ordenacao_normalizada = str(ordenacao or "prontos").strip().lower()
    canal_resolvido = canal
    if not canal_resolvido:
        canal_resolvido = x_canal_venda
    if not canal_resolvido and authorization:
        # Compatibilidade com versões antigas do app que não enviam query/header de canal.
        canal_resolvido = "app"
    canal_normalizado = _normalize_sales_channel(canal_resolvido)

    if ordenacao_normalizada not in _CATALOG_ORDER_OPTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ordenação inválida. Use: prontos, nome, menor_preco ou maior_preco.",
        )

    # Fonte única de estoque: saldo oficial do Sistema Pet.
    estoque_catalogo = func.coalesce(Produto.estoque_atual, 0)
    tem_imagem_expr = or_(
        and_(
            Produto.imagem_principal.is_not(None),
            func.length(func.trim(Produto.imagem_principal)) > 0,
        ),
        Produto.imagens.any(),
    )
    prioridade_estoque = case((estoque_catalogo > 0, 0), else_=1)
    prioridade_imagem = case((tem_imagem_expr, 0), else_=1)
    if canal_normalizado == "app":
        preco_catalogo = func.coalesce(Produto.preco_app, Produto.preco_venda, 0)
    else:
        preco_catalogo = func.coalesce(Produto.preco_ecommerce, Produto.preco_venda, 0)

    query = (
        db.query(Produto)
        .options(
            joinedload(Produto.categoria),
            joinedload(Produto.marca),
            selectinload(Produto.imagens),
        )
        .filter(
            Produto.tenant_id == tenant.id,
            Produto.ativo == True,
            Produto.situacao.is_not(False),
            Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
        )
    )

    if canal_normalizado == "app":
        query = query.filter(Produto.anunciar_app.is_(True))
    else:
        query = query.filter(Produto.anunciar_ecommerce.is_(True))

    if busca:
        termo = busca.strip()
        like_termo = f"%{termo}%"
        query = query.filter(
            or_(
                func.unaccent(Produto.nome).ilike(func.unaccent(like_termo)),
                Produto.codigo.ilike(like_termo),
                Produto.codigo_barras.ilike(like_termo),
            )
        )

    if apenas_com_estoque:
        query = query.filter(estoque_catalogo > 0)

    if apenas_com_imagem:
        query = query.filter(tem_imagem_expr)

    total = query.count()

    if ordenacao_normalizada == "nome":
        query = query.order_by(func.lower(Produto.nome).asc(), Produto.id.asc())
    elif ordenacao_normalizada == "menor_preco":
        query = query.order_by(preco_catalogo.asc(), func.lower(Produto.nome).asc(), Produto.id.asc())
    elif ordenacao_normalizada == "maior_preco":
        query = query.order_by(preco_catalogo.desc(), func.lower(Produto.nome).asc(), Produto.id.asc())
    else:
        query = query.order_by(
            prioridade_estoque.asc(),
            prioridade_imagem.asc(),
            estoque_catalogo.desc(),
            func.lower(Produto.nome).asc(),
            Produto.id.asc(),
        )

    itens = query.offset(offset).limit(limit).all()
    ofertas_validade = mapear_ofertas_validade_por_produto(db, itens, canal_normalizado)

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            (lambda pricing, oferta: {
                "id": produto.id,
                "nome": produto.nome,
                "codigo": produto.codigo,
                "codigo_barras": produto.codigo_barras,
                "preco_venda": pricing.regular_price,
                "preco_promocional": pricing.promotional_price,
                "promocao_ativa": pricing.promotion_active,
                "promocao_origem": pricing.promotion_origin,
                "promocao_validade": _serializar_promocao_validade(
                    oferta,
                    pricing.promotion_origin,
                ),
                "categoria_id": produto.categoria_id,
                "categoria_nome": getattr(produto.categoria, "nome", None),
                "marca_nome": getattr(produto.marca, "nome", None) if hasattr(produto, "marca") else None,
                # Mantemos o campo por compatibilidade, mas com o mesmo saldo oficial.
                "estoque_ecommerce": produto.estoque_atual,
                "estoque_atual": produto.estoque_atual,
                "imagem_principal": produto.imagem_principal,
                "imagens": [
                    {
                        "id": imagem.id,
                        "url": imagem.url,
                        "ordem": imagem.ordem,
                        "e_principal": imagem.e_principal,
                    }
                    for imagem in sorted(produto.imagens or [], key=lambda item: (item.ordem or 0, item.id or 0))
                ],
                "descricao": produto.descricao_curta or produto.descricao_completa,
                "peso_embalagem": produto.peso_embalagem,
                "classificacao_racao": produto.classificacao_racao,
                "categoria_racao": produto.categoria_racao,
            })(
                resolver_preco_publico_produto(
                    produto,
                    canal_normalizado,
                    validity_offer=ofertas_validade.get(produto.id),
                ),
                ofertas_validade.get(produto.id),
            )
            for produto in itens
        ],
    }
