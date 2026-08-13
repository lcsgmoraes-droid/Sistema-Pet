import re
import unicodedata
from math import asin, cos, radians, sin, sqrt
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, distinct, func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db import get_session
from app.ecommerce_analytics_models import EcommerceAnalyticsEvent
from app.models import Tenant
from app.produtos_models import Categoria, Marca, Produto
from app.services.validade_campanha_service import (
    mapear_ofertas_validade_por_produto,
    resolver_preco_publico_produto,
)
from app.tenant_identity import normalize_tenant_name
from app.tenancy.context import set_current_tenant


router = APIRouter(prefix="/ecommerce", tags=["ecommerce-public"])
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CATALOG_ORDER_OPTIONS = {
    "prontos",
    "relevancia",
    "nome",
    "nome_asc",
    "menor_preco",
    "maior_preco",
}
_CATALOG_ORDER_ALIASES = {
    "relevancia": "prontos",
    "nome_asc": "nome",
}
_ANALYTICS_EVENT_NAMES = {
    "page_view",
    "view_item",
    "search",
    "add_to_cart",
    "view_cart",
    "begin_checkout",
    "checkout_submitted",
    "purchase",
}


def _normalize_location_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", str(value).strip().lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


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


def _normalize_catalog_order(raw_order: str | None) -> str:
    value = str(raw_order or "prontos").strip().lower()
    normalized = _CATALOG_ORDER_ALIASES.get(value, value)
    if normalized not in {"prontos", "nome", "menor_preco", "maior_preco"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ordenacao invalida. Use: relevancia, nome_asc, menor_preco ou maior_preco.",
        )
    return normalized


def _normalize_catalog_brand_names(rows) -> list[str]:
    names = {
        str(row[0]).strip() for row in rows if row and row[0] and str(row[0]).strip()
    }
    return sorted(names, key=str.casefold)


def _split_legacy_category_path(value: str | None) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"\s*(?:>>|>|/|\\)\s*", str(value or ""))
        if item.strip()
    ]


def _build_category_path_map(db: Session, tenant_id) -> dict[int, list[str]]:
    rows = (
        db.query(Categoria.id, Categoria.nome, Categoria.categoria_pai_id)
        .filter(Categoria.tenant_id == tenant_id)
        .all()
    )
    by_id = {
        int(row.id): {
            "nome": str(row.nome or "Sem categoria").strip(),
            "pai": int(row.categoria_pai_id) if row.categoria_pai_id else None,
        }
        for row in rows
    }
    cache: dict[int, list[str]] = {}

    def resolve(category_id: int, seen: set[int] | None = None) -> list[str]:
        if category_id in cache:
            return cache[category_id]
        current = by_id.get(category_id)
        if not current:
            return []
        legacy_parts = _split_legacy_category_path(current["nome"])
        if len(legacy_parts) > 1:
            cache[category_id] = legacy_parts
            return legacy_parts
        seen = set(seen or set())
        if category_id in seen:
            return legacy_parts or [current["nome"]]
        seen.add(category_id)
        parent_parts = (
            resolve(current["pai"], seen) if current.get("pai") is not None else []
        )
        cache[category_id] = [*parent_parts, *(legacy_parts or [current["nome"]])]
        return cache[category_id]

    for category_id in by_id:
        resolve(category_id)
    return cache


def _serialize_catalog_categories(rows, path_map: dict[int, list[str]]) -> list[dict]:
    categorias = []
    for row in rows:
        category_id = getattr(row, "id", None)
        category_name = getattr(row, "nome", None) or "Sem categoria"
        total = int(getattr(row, "total", 0) or 0)
        if category_id is None:
            continue
        parts = path_map.get(int(category_id)) or _split_legacy_category_path(
            category_name
        )
        if not parts:
            parts = ["Sem categoria"]
        categorias.append(
            {
                "id": int(category_id),
                "nome": parts[-1],
                "nome_original": category_name,
                "caminho": " > ".join(parts),
                "caminho_partes": parts,
                "grupo": parts[0] if len(parts) > 1 else "Outros",
                "nivel": len(parts) - 1,
                "total": total,
            }
        )
    return categorias


def _serialize_catalog_product(
    produto: Produto,
    canal_normalizado: str,
    oferta=None,
    tenant: Tenant | None = None,
) -> dict:
    pricing = resolver_preco_publico_produto(
        produto,
        canal_normalizado,
        validity_offer=oferta,
    )
    return {
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
        "marca_nome": getattr(produto.marca, "nome", None)
        if hasattr(produto, "marca")
        else None,
        "estoque_ecommerce": (
            produto.estoque_ecommerce
            if tenant is not None and tenant.ecommerce_usar_estoque_canal
            else produto.estoque_atual
        ),
        "estoque_atual": (
            produto.estoque_ecommerce
            if tenant is not None and tenant.ecommerce_usar_estoque_canal
            else produto.estoque_atual
        ),
        "imagem_principal": produto.imagem_principal,
        "imagens": [
            {
                "id": imagem.id,
                "url": imagem.url,
                "ordem": imagem.ordem,
                "e_principal": imagem.e_principal,
            }
            for imagem in sorted(
                produto.imagens or [],
                key=lambda item: (item.ordem or 0, item.id or 0),
            )
        ],
        "descricao": produto.descricao_curta or produto.descricao_completa,
        "peso_embalagem": produto.peso_embalagem,
        "classificacao_racao": produto.classificacao_racao,
        "categoria_racao": produto.categoria_racao,
        "unidade": produto.unidade or "UN",
        "produto_pai_id": produto.produto_pai_id,
        "tipo_produto": produto.tipo_produto,
        "variation_attributes": produto.variation_attributes or {},
    }


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
        tenant = (
            db.query(Tenant).filter(func.lower(Tenant.ecommerce_slug) == value).first()
        )

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
    if getattr(tenant, "ecommerce_ativo", True) is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta loja online está fechada no momento.",
        )
    set_current_tenant(UUID(str(tenant.id)))
    return tenant


def _distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Return the great-circle distance between two coordinates."""
    earth_radius_km = 6371.0088
    latitude_delta = radians(latitude_b - latitude_a)
    longitude_delta = radians(longitude_b - longitude_a)
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(latitude_a))
        * cos(radians(latitude_b))
        * sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(min(1.0, haversine)))


def _tenant_public_payload(
    tenant: Tenant,
    distancia_km: float | None = None,
) -> dict:
    payload = {
        "id": str(tenant.id),
        "slug": tenant.ecommerce_slug,
        "nome": tenant.name,
        "name": tenant.name,
        "logo_url": tenant.logo_url,
        "endereco": tenant.endereco,
        "numero": tenant.numero,
        "bairro": tenant.bairro,
        "cep": tenant.cep,
        "cidade": tenant.cidade,
        "uf": tenant.uf,
        "telefone": getattr(tenant, "telefone", None),
        "email": getattr(tenant, "email", None),
        "ecommerce_descricao": getattr(tenant, "ecommerce_descricao", None),
        "ecommerce_horario_abertura": getattr(
            tenant, "ecommerce_horario_abertura", None
        ),
        "ecommerce_horario_fechamento": getattr(
            tenant, "ecommerce_horario_fechamento", None
        ),
        "ecommerce_dias_funcionamento": getattr(
            tenant, "ecommerce_dias_funcionamento", None
        ),
        "ecommerce_entrega_ativa": bool(
            getattr(tenant, "ecommerce_entrega_ativa", True)
        ),
        "ecommerce_retirada_ativa": bool(
            getattr(tenant, "ecommerce_retirada_ativa", True)
        ),
        "ecommerce_taxa_entrega": float(
            getattr(tenant, "ecommerce_taxa_entrega", 0) or 0
        ),
        "ecommerce_frete_gratis_acima": (
            float(getattr(tenant, "ecommerce_frete_gratis_acima"))
            if getattr(tenant, "ecommerce_frete_gratis_acima", None) is not None
            else None
        ),
        "ecommerce_pedido_minimo": float(
            getattr(tenant, "ecommerce_pedido_minimo", 0) or 0
        ),
        "ecommerce_prazo_entrega_texto": getattr(
            tenant, "ecommerce_prazo_entrega_texto", None
        ),
        "ecommerce_cor_primaria": getattr(tenant, "ecommerce_cor_primaria", None)
        or "#f97316",
        "ecommerce_cor_secundaria": getattr(tenant, "ecommerce_cor_secundaria", None)
        or "#0f766e",
    }
    if distancia_km is not None:
        payload["distancia_km"] = round(distancia_km, 1)
    return payload


@router.get("/tenants/sugerir")
def sugerir_tenants_por_localidade(
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    cidade: str | None = Query(default=None, min_length=2),
    uf: str | None = Query(default=None, min_length=2, max_length=2),
    limit: int = Query(default=8, ge=1, le=8),
    db: Session = Depends(get_session),
):
    """Suggest up to eight active stores, prioritizing real GPS distance."""
    has_coordinates = latitude is not None and longitude is not None
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe latitude e longitude juntas.",
        )
    if not has_coordinates and not cidade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe a localizacao ou a cidade.",
        )

    cidade_norm = _normalize_location_text(cidade)
    uf_norm = uf.strip().upper() if uf else None

    filtros = [
        Tenant.ecommerce_slug.isnot(None),
        Tenant.ecommerce_slug != "",
        func.lower(Tenant.status) == "active",
        Tenant.ecommerce_ativo.is_(True),
    ]
    candidates = db.query(Tenant).filter(*filtros).order_by(Tenant.name.asc()).all()

    if has_coordinates:
        located: list[tuple[Tenant, float]] = []
        fallback: list[Tenant] = []
        for tenant in candidates:
            if tenant.latitude is not None and tenant.longitude is not None:
                located.append(
                    (
                        tenant,
                        _distance_km(
                            float(latitude),
                            float(longitude),
                            float(tenant.latitude),
                            float(tenant.longitude),
                        ),
                    )
                )
            elif cidade_norm and _normalize_location_text(tenant.cidade) == cidade_norm:
                if not uf_norm or str(tenant.uf or "").upper() == uf_norm:
                    fallback.append(tenant)

        located.sort(key=lambda item: (item[1], str(item[0].name).lower()))
        payloads = [
            _tenant_public_payload(tenant, distance)
            for tenant, distance in located[:limit]
        ]
        if len(payloads) < limit:
            payloads.extend(
                _tenant_public_payload(tenant)
                for tenant in fallback[: limit - len(payloads)]
            )
        return {"lojas": payloads}

    local_tenants = [
        tenant
        for tenant in candidates
        if _normalize_location_text(tenant.cidade) == cidade_norm
        and (not uf_norm or str(tenant.uf or "").upper() == uf_norm)
    ][:limit]
    return {"lojas": [_tenant_public_payload(tenant) for tenant in local_tenants]}


@router.get("/tenants/buscar")
def buscar_tenants_por_nome(
    q: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_session),
):
    """Search active stores by name without applying a geographic boundary."""
    query_normalized = normalize_tenant_name(q)
    matches = (
        db.query(Tenant)
        .filter(
            Tenant.ecommerce_slug.isnot(None),
            Tenant.ecommerce_slug != "",
            func.lower(Tenant.status) == "active",
            Tenant.ecommerce_ativo.is_(True),
            Tenant.name_normalized.contains(query_normalized),
        )
        .order_by(
            case(
                (Tenant.name_normalized == query_normalized, 0),
                (Tenant.name_normalized.startswith(query_normalized), 1),
                else_=2,
            ),
            Tenant.name_normalized.asc(),
        )
        .limit(limit)
        .all()
    )
    return {"lojas": [_tenant_public_payload(tenant) for tenant in matches]}


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

    tenant = (
        db.query(Tenant).filter(func.lower(Tenant.ecommerce_slug) == slug_norm).first()
    )

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
    if getattr(tenant, "ecommerce_ativo", True) is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta loja online está fechada no momento.",
        )

    return _tenant_public_payload(tenant)


@router.get("/tenant-context")
def tenant_context(
    tenant_ref: tuple[str, str] = Depends(_resolve_tenant_ref),
    db: Session = Depends(get_session),
):
    tenant = _get_active_tenant(db, tenant_ref)
    storefront_ref = tenant.ecommerce_slug or tenant.id
    return {
        **_tenant_public_payload(tenant),
        "id": tenant.id,
        "name": tenant.name,
        "ecommerce_slug": tenant.ecommerce_slug,
        "storefront_path": f"/{storefront_ref}",
        "status": tenant.status,
        "banner_1_url": tenant.banner_1_url,
        "banner_2_url": tenant.banner_2_url,
        "banner_3_url": tenant.banner_3_url,
    }


class EcommerceAnalyticsEventCreate(BaseModel):
    event_name: str = Field(min_length=2, max_length=40)
    session_id: str = Field(
        min_length=8,
        max_length=80,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    channel: str = Field(default="ecommerce", max_length=20)
    path: str | None = Field(default=None, max_length=300)
    product_id: int | None = Field(default=None, ge=1)
    pedido_id: str | None = Field(default=None, max_length=80)
    value: float | None = Field(default=None, ge=0)
    extra_data: dict | None = None


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
def registrar_evento_analytics_publico(
    body: EcommerceAnalyticsEventCreate,
    tenant_ref: tuple[str, str] = Depends(_resolve_tenant_ref),
    db: Session = Depends(get_session),
):
    tenant = _get_active_tenant(db, tenant_ref)
    event_name = body.event_name.strip().lower()
    if event_name not in _ANALYTICS_EVENT_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evento de analytics inválido.",
        )
    extra_data = body.extra_data if isinstance(body.extra_data, dict) else None
    if extra_data and len(str(extra_data)) > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metadados do evento muito grandes.",
        )
    db.add(
        EcommerceAnalyticsEvent(
            tenant_id=UUID(str(tenant.id)),
            event_name=event_name,
            session_id=body.session_id,
            channel=_normalize_sales_channel(body.channel),
            path=body.path,
            product_id=body.product_id,
            pedido_id=body.pedido_id,
            value=body.value,
            extra_data=extra_data,
        )
    )
    db.commit()
    return {"status": "accepted"}


@router.get("/produtos/filtros")
def listar_filtros_produtos_publicos(
    tenant_ref: tuple[str, str] = Depends(_resolve_tenant_ref),
    busca: str | None = Query(default=None),
    canal: str | None = Query(default=None),
    x_canal_venda: str | None = Header(default=None, alias="X-Canal-Venda"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_session),
):
    tenant = _get_active_tenant(db, tenant_ref)
    canal_resolvido = canal or x_canal_venda
    if not canal_resolvido and authorization:
        canal_resolvido = "app"
    canal_normalizado = _normalize_sales_channel(canal_resolvido)

    base_filters = [
        Produto.tenant_id == tenant.id,
        Produto.ativo.is_(True),
        Produto.situacao.is_not(False),
        Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
    ]
    estoque_catalogo = func.coalesce(
        Produto.estoque_ecommerce
        if tenant.ecommerce_usar_estoque_canal
        else Produto.estoque_atual,
        0,
    )
    tem_imagem_expr = or_(
        and_(
            Produto.imagem_principal.is_not(None),
            func.length(func.trim(Produto.imagem_principal)) > 0,
        ),
        Produto.imagens.any(),
    )
    if tenant.ecommerce_ocultar_servicos:
        base_filters.append(
            func.lower(func.coalesce(Produto.tipo, "produto")) != "servico"
        )
    if tenant.ecommerce_ocultar_sem_estoque:
        base_filters.append(estoque_catalogo > 0)
    if tenant.ecommerce_ocultar_sem_imagem:
        base_filters.append(tem_imagem_expr)

    if canal_normalizado == "app":
        base_filters.append(Produto.anunciar_app.is_(True))
    else:
        base_filters.append(Produto.anunciar_ecommerce.is_(True))

    if busca:
        termo = busca.strip()
        like_termo = f"%{termo}%"
        base_filters.append(
            or_(
                func.unaccent(Produto.nome).ilike(func.unaccent(like_termo)),
                Produto.codigo.ilike(like_termo),
                Produto.codigo_barras.ilike(like_termo),
            )
        )

    marcas = (
        db.query(Marca.nome)
        .join(Produto, Produto.marca_id == Marca.id)
        .filter(
            *base_filters,
            Marca.nome.isnot(None),
            func.length(func.trim(Marca.nome)) > 0,
        )
        .distinct()
        .all()
    )
    pesos = (
        db.query(distinct(Produto.peso_embalagem))
        .filter(
            *base_filters,
            Produto.peso_embalagem.isnot(None),
            Produto.peso_embalagem > 0,
        )
        .order_by(Produto.peso_embalagem.asc())
        .all()
    )

    return {
        "marcas": _normalize_catalog_brand_names(marcas),
        "pesos_embalagem_kg": [
            round(float(row[0]), 3)
            for row in pesos
            if row[0] is not None and float(row[0]) > 0
        ],
    }


@router.get("/products/{produto_id}")
def obter_produto_publico_por_id(
    produto_id: int,
    tenant_ref: tuple[str, str] = Depends(_resolve_tenant_ref),
    canal: str | None = Query(default=None),
    x_canal_venda: str | None = Header(default=None, alias="X-Canal-Venda"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_session),
):
    tenant = _get_active_tenant(db, tenant_ref)
    canal_resolvido = canal or x_canal_venda
    if not canal_resolvido and authorization:
        canal_resolvido = "app"
    canal_normalizado = _normalize_sales_channel(canal_resolvido)

    query = (
        db.query(Produto)
        .options(
            joinedload(Produto.categoria),
            joinedload(Produto.marca),
            selectinload(Produto.imagens),
        )
        .filter(
            Produto.tenant_id == tenant.id,
            Produto.id == produto_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
            Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
        )
    )
    if canal_normalizado == "app":
        query = query.filter(Produto.anunciar_app.is_(True))
    else:
        query = query.filter(Produto.anunciar_ecommerce.is_(True))
    if tenant.ecommerce_ocultar_servicos:
        query = query.filter(
            func.lower(func.coalesce(Produto.tipo, "produto")) != "servico"
        )
    if tenant.ecommerce_ocultar_sem_estoque:
        estoque_catalogo = func.coalesce(
            Produto.estoque_ecommerce
            if tenant.ecommerce_usar_estoque_canal
            else Produto.estoque_atual,
            0,
        )
        query = query.filter(estoque_catalogo > 0)
    if tenant.ecommerce_ocultar_sem_imagem:
        query = query.filter(
            or_(
                and_(
                    Produto.imagem_principal.is_not(None),
                    func.length(func.trim(Produto.imagem_principal)) > 0,
                ),
                Produto.imagens.any(),
            )
        )

    produto = query.first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado.")

    oferta = mapear_ofertas_validade_por_produto(db, [produto], canal_normalizado).get(
        produto.id
    )
    return _serialize_catalog_product(
        produto,
        canal_normalizado,
        oferta,
        tenant=tenant,
    )


@router.get("/produtos")
def listar_produtos_publicos(
    tenant_ref: tuple[str, str] = Depends(_resolve_tenant_ref),
    busca: str | None = Query(default=None),
    categoria_id: int | None = Query(default=None, ge=1),
    categoria_ids: list[int] | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    apenas_com_estoque: bool = Query(default=False),
    apenas_com_imagem: bool = Query(default=False),
    ordenacao: str = Query(default="prontos"),
    marca: str | None = Query(default=None),
    peso_embalagem_kg: float | None = Query(default=None),
    preco_minimo: float | None = Query(default=None, ge=0),
    preco_maximo: float | None = Query(default=None, ge=0),
    canal: str | None = Query(default=None),
    x_canal_venda: str | None = Header(default=None, alias="X-Canal-Venda"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_session),
):
    tenant = _get_active_tenant(db, tenant_ref)
    ordenacao_normalizada = _normalize_catalog_order(ordenacao)
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
    estoque_catalogo = func.coalesce(
        Produto.estoque_ecommerce
        if tenant.ecommerce_usar_estoque_canal
        else Produto.estoque_atual,
        0,
    )
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

    base_filters = [
        Produto.tenant_id == tenant.id,
        Produto.ativo.is_(True),
        Produto.situacao.is_not(False),
        Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
    ]
    if tenant.ecommerce_ocultar_servicos:
        base_filters.append(
            func.lower(func.coalesce(Produto.tipo, "produto")) != "servico"
        )

    query = (
        db.query(Produto)
        .options(
            joinedload(Produto.categoria),
            joinedload(Produto.marca),
            selectinload(Produto.imagens),
        )
        .filter(*base_filters)
    )
    category_name_expr = func.coalesce(Categoria.nome, "Sem categoria")
    categorias_query = (
        db.query(
            Produto.categoria_id.label("id"),
            category_name_expr.label("nome"),
            func.count(Produto.id).label("total"),
        )
        .outerjoin(Categoria, Produto.categoria_id == Categoria.id)
        .filter(*base_filters)
    )

    if canal_normalizado == "app":
        query = query.filter(Produto.anunciar_app.is_(True))
        categorias_query = categorias_query.filter(Produto.anunciar_app.is_(True))
    else:
        query = query.filter(Produto.anunciar_ecommerce.is_(True))
        categorias_query = categorias_query.filter(Produto.anunciar_ecommerce.is_(True))

    if busca:
        termo = busca.strip()
        like_termo = f"%{termo}%"
        busca_filter = or_(
            func.unaccent(Produto.nome).ilike(func.unaccent(like_termo)),
            Produto.codigo.ilike(like_termo),
            Produto.codigo_barras.ilike(like_termo),
        )
        query = query.filter(busca_filter)
        categorias_query = categorias_query.filter(busca_filter)

    if apenas_com_estoque or tenant.ecommerce_ocultar_sem_estoque:
        query = query.filter(estoque_catalogo > 0)
        categorias_query = categorias_query.filter(estoque_catalogo > 0)

    if apenas_com_imagem or tenant.ecommerce_ocultar_sem_imagem:
        query = query.filter(tem_imagem_expr)
        categorias_query = categorias_query.filter(tem_imagem_expr)

    if marca:
        marca_norm = marca.strip().lower()
        marca_filter = Produto.marca.has(func.lower(Marca.nome) == marca_norm)
        query = query.filter(marca_filter)
        categorias_query = categorias_query.filter(marca_filter)

    if peso_embalagem_kg is not None and peso_embalagem_kg > 0:
        margem_peso = 0.001
        peso_filter = and_(
            Produto.peso_embalagem >= peso_embalagem_kg - margem_peso,
            Produto.peso_embalagem <= peso_embalagem_kg + margem_peso,
        )
        query = query.filter(peso_filter)
        categorias_query = categorias_query.filter(peso_filter)

    if preco_minimo is not None:
        query = query.filter(preco_catalogo >= preco_minimo)
        categorias_query = categorias_query.filter(preco_catalogo >= preco_minimo)
    if preco_maximo is not None:
        query = query.filter(preco_catalogo <= preco_maximo)
        categorias_query = categorias_query.filter(preco_catalogo <= preco_maximo)

    categorias = _serialize_catalog_categories(
        categorias_query.group_by(Produto.categoria_id, category_name_expr)
        .order_by(func.lower(category_name_expr).asc())
        .all(),
        _build_category_path_map(db, tenant.id),
    )

    selected_category_ids = {
        int(value)
        for value in [
            *(categoria_ids or []),
            *([categoria_id] if categoria_id is not None else []),
        ]
        if int(value) > 0
    }
    if selected_category_ids:
        query = query.filter(Produto.categoria_id.in_(selected_category_ids))

    total = query.count()

    if ordenacao_normalizada == "nome":
        query = query.order_by(func.lower(Produto.nome).asc(), Produto.id.asc())
    elif ordenacao_normalizada == "menor_preco":
        query = query.order_by(
            preco_catalogo.asc(), func.lower(Produto.nome).asc(), Produto.id.asc()
        )
    elif ordenacao_normalizada == "maior_preco":
        query = query.order_by(
            preco_catalogo.desc(), func.lower(Produto.nome).asc(), Produto.id.asc()
        )
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
        "categorias": categorias,
        "items": [
            _serialize_catalog_product(
                produto,
                canal_normalizado,
                ofertas_validade.get(produto.id),
                tenant=tenant,
            )
            for produto in itens
        ],
    }
