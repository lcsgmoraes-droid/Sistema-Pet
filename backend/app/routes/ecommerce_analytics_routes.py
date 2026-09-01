"""Analytics operacional da loja virtual, com período e canal."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.ecommerce_analytics_models import EcommerceAnalyticsEvent
from app.models import EcommerceNotifyRequest, Tenant
from app.pedido_models import Pedido, PedidoItem
from app.produtos_models import Produto
from app.security.permissions_decorator import require_any_permission
from app.services.ecommerce_catalog_health import (
    catalog_published_expression,
    classify_catalog_product,
)

router = APIRouter(prefix="/ecommerce-analytics", tags=["ecommerce-analytics"])

STATUS_PAGOS = ("aprovado", "finalizado", "pago", "entregue")
ORIGENS_POR_CANAL = {
    "ecommerce": ("web", "ecommerce"),
    "app": ("app",),
    "marketplace": ("marketplace",),
    "todos": ("web", "ecommerce", "app", "marketplace"),
}
_ANALYTICS_PERMISSIONS = (
    "relatorios.gerencial",
    "vendas.visualizar",
    "configuracoes.editar",
)
_BRASILIA = ZoneInfo("America/Sao_Paulo")


def _period_start(dias: int) -> datetime:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=max(1, min(int(dias), 3650)))


def _channel_origins(canal: str) -> tuple[str, ...]:
    return ORIGENS_POR_CANAL.get(
        str(canal or "").lower(), ORIGENS_POR_CANAL["ecommerce"]
    )


def _pedido_filters(tenant_id, dias: int, canal: str):
    return (
        Pedido.tenant_id == tenant_id,
        Pedido.created_at >= _period_start(dias),
        Pedido.origem.in_(_channel_origins(canal)),
    )


@router.get("/resumo")
@require_any_permission(_ANALYTICS_PERMISSIONS)
def get_resumo(
    dias: int = Query(default=30, ge=1, le=3650),
    canal: str = Query(default="ecommerce"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    filters = _pedido_filters(tenant_id, dias, canal)

    total_pedidos, receita_total = (
        db.query(
            func.count(Pedido.id),
            func.coalesce(func.sum(Pedido.total), 0),
        )
        .filter(*filters, Pedido.status.in_(STATUS_PAGOS))
        .one()
    )
    total_pedidos = int(total_pedidos or 0)
    receita_total = float(receita_total or 0)

    hoje_brasilia = datetime.now(_BRASILIA).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    hoje_utc = hoje_brasilia.astimezone(timezone.utc)
    pedidos_hoje = (
        db.query(func.count(Pedido.id))
        .filter(
            Pedido.tenant_id == tenant_id,
            Pedido.created_at >= hoje_utc,
            Pedido.origem.in_(_channel_origins(canal)),
            Pedido.status.in_(STATUS_PAGOS),
        )
        .scalar()
        or 0
    )

    carrinhos_abandonados = (
        db.query(func.count(Pedido.id))
        .filter(
            *filters,
            Pedido.status == "carrinho",
            Pedido.created_at <= datetime.now(timezone.utc) - timedelta(hours=1),
        )
        .scalar()
        or 0
    )
    avise_me_pendentes = (
        db.query(func.count(EcommerceNotifyRequest.id))
        .filter(
            EcommerceNotifyRequest.tenant_id == tenant_id,
            EcommerceNotifyRequest.notified.is_(False),
        )
        .scalar()
        or 0
    )
    status_counts = (
        db.query(Pedido.status, func.count(Pedido.id))
        .filter(*filters)
        .group_by(Pedido.status)
        .all()
    )

    return {
        "periodo_dias": dias,
        "canal": canal,
        "total_pedidos": total_pedidos,
        "receita_total": round(receita_total, 2),
        "ticket_medio": round(
            receita_total / total_pedidos if total_pedidos else 0,
            2,
        ),
        "pedidos_hoje": int(pedidos_hoje),
        "carrinhos_abandonados": int(carrinhos_abandonados),
        "avise_me_pendentes": int(avise_me_pendentes),
        "pedidos_por_status": {status: int(total) for status, total in status_counts},
    }


@router.get("/funil")
@require_any_permission(_ANALYTICS_PERMISSIONS)
def get_funil(
    dias: int = Query(default=30, ge=1, le=3650),
    canal: str = Query(default="ecommerce"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    event_query = db.query(
        EcommerceAnalyticsEvent.event_name,
        func.count(EcommerceAnalyticsEvent.id).label("eventos"),
        func.count(func.distinct(EcommerceAnalyticsEvent.session_id)).label("sessoes"),
    ).filter(
        EcommerceAnalyticsEvent.tenant_id == tenant_id,
        EcommerceAnalyticsEvent.created_at >= _period_start(dias),
    )
    if canal != "todos":
        event_query = event_query.filter(EcommerceAnalyticsEvent.channel == canal)
    rows = event_query.group_by(EcommerceAnalyticsEvent.event_name).all()
    by_name = {
        row.event_name: {
            "eventos": int(row.eventos or 0),
            "sessoes": int(row.sessoes or 0),
        }
        for row in rows
    }
    approved_orders = (
        db.query(func.count(Pedido.id))
        .filter(
            *_pedido_filters(tenant_id, dias, canal),
            Pedido.status.in_(STATUS_PAGOS),
        )
        .scalar()
        or 0
    )
    by_name["purchase"] = {
        "eventos": int(approved_orders),
        "sessoes": int(approved_orders),
    }
    steps = [
        ("page_view", "Visitas"),
        ("view_item", "Produtos vistos"),
        ("add_to_cart", "Adicionaram ao carrinho"),
        ("begin_checkout", "Iniciaram checkout"),
        ("checkout_submitted", "Foram ao pagamento"),
        ("purchase", "Compras aprovadas"),
    ]
    visitas = by_name.get("page_view", {}).get("sessoes", 0)
    return {
        "periodo_dias": dias,
        "canal": canal,
        "etapas": [
            {
                "evento": event_name,
                "label": label,
                **by_name.get(event_name, {"eventos": 0, "sessoes": 0}),
                "conversao_visita": round(
                    (by_name.get(event_name, {}).get("sessoes", 0) / visitas * 100)
                    if visitas
                    else 0,
                    2,
                ),
            }
            for event_name, label in steps
        ],
    }


def _catalog_health_data(
    db: Session, tenant_id, channel: str
) -> tuple[Tenant, list[dict]]:
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    products = (
        db.query(Produto)
        .options(
            joinedload(Produto.categoria),
            joinedload(Produto.marca),
            selectinload(Produto.imagens),
        )
        .filter(
            Produto.tenant_id == tenant_id,
            catalog_published_expression(channel),
        )
        .all()
    )
    waitlist = dict(
        db.query(
            EcommerceNotifyRequest.product_id,
            func.count(EcommerceNotifyRequest.id),
        )
        .filter(
            EcommerceNotifyRequest.tenant_id == tenant_id,
            EcommerceNotifyRequest.notified.is_(False),
        )
        .group_by(EcommerceNotifyRequest.product_id)
        .all()
    )
    rows = []
    for product in products:
        health = classify_catalog_product(
            product,
            tenant,
            channel,
            waitlist_count=int(waitlist.get(product.id, 0) or 0),
        )
        rows.append(
            {
                **health,
                "id": product.id,
                "codigo": product.codigo,
                "nome": product.nome,
                "imagem_principal": product.imagem_principal,
                "categoria_nome": getattr(product.categoria, "nome", None),
                "marca_nome": getattr(product.marca, "nome", None),
            }
        )
    return tenant, rows


def _catalog_health_summary(rows: list[dict]) -> dict:
    published = len(rows)
    issue_counts = {
        "sem_estoque": sum(row["estoque"] <= 0 for row in rows),
        "sem_preco": 0,
        "sem_imagem": 0,
        "sem_descricao": 0,
        "sem_categoria": 0,
        "sem_marca": 0,
    }
    for row in rows:
        codes = {item["codigo"] for item in [*row["bloqueios"], *row["pendencias"]]}
        issue_counts["sem_preco"] += "sem_preco" in codes
        issue_counts["sem_imagem"] += bool(
            {"sem_imagem", "sem_imagem_bloqueante"}.intersection(codes)
        )
        for code in ("sem_descricao", "sem_categoria", "sem_marca"):
            issue_counts[code] += code in codes

    purchasable = sum(bool(row["compravel"]) for row in rows)
    return {
        "publicados": published,
        "visiveis": sum(bool(row["visivel"]) for row in rows),
        "prontos_para_venda": purchasable,
        "sem_pendencias": sum(row["status"] == "pronto" for row in rows),
        "bloqueados": sum(row["status"] == "bloqueado" for row in rows),
        "esgotados": sum(row["status"] == "esgotado" for row in rows),
        "com_pendencias": sum(row["status"] == "pendencias" for row in rows),
        "percentual_pronto": round(
            (purchasable / published * 100) if published else 0,
            2,
        ),
        **{key: int(value) for key, value in issue_counts.items()},
    }


@router.get("/catalogo-saude")
@require_any_permission(_ANALYTICS_PERMISSIONS)
def get_catalogo_saude(
    canal: str = Query(default="ecommerce", pattern="^(ecommerce|app)$"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tenant, rows = _catalog_health_data(db, tenant_id, canal)
    return {
        **_catalog_health_summary(rows),
        "canal": canal,
        "exibir_esgotados": not bool(tenant.ecommerce_ocultar_sem_estoque),
    }


@router.get("/catalogo-saude/produtos")
@require_any_permission(_ANALYTICS_PERMISSIONS)
def get_catalogo_saude_produtos(
    canal: str = Query(default="ecommerce", pattern="^(ecommerce|app)$"),
    situacao: str = Query(
        default="todos", pattern="^(todos|bloqueado|esgotado|pendencias|pronto)$"
    ),
    problema: str | None = Query(default=None),
    busca: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tenant, rows = _catalog_health_data(db, tenant_id, canal)
    summary = _catalog_health_summary(rows)

    filtered = rows
    if situacao != "todos":
        filtered = [row for row in filtered if row["status"] == situacao]
    if problema:
        normalized_problem = problema.strip().lower()

        def has_problem(row):
            if normalized_problem == "sem_estoque":
                return row["estoque"] <= 0
            codes = {item["codigo"] for item in [*row["bloqueios"], *row["pendencias"]]}
            if normalized_problem == "sem_imagem":
                return bool({"sem_imagem", "sem_imagem_bloqueante"}.intersection(codes))
            return normalized_problem in codes

        filtered = [row for row in filtered if has_problem(row)]
    if busca and busca.strip():
        term = busca.strip().casefold()
        filtered = [
            row
            for row in filtered
            if term in str(row["nome"] or "").casefold()
            or term in str(row["codigo"] or "").casefold()
        ]

    order = {"bloqueado": 0, "esgotado": 1, "pendencias": 2, "pronto": 3}
    filtered.sort(
        key=lambda row: (
            -int(row["avise_me_pendentes"] or 0),
            order.get(row["status"], 9),
            str(row["nome"] or "").casefold(),
        )
    )
    total = len(filtered)
    return {
        "canal": canal,
        "configuracao": {
            "exibir_esgotados": not bool(tenant.ecommerce_ocultar_sem_estoque),
            "ocultar_sem_imagem": bool(tenant.ecommerce_ocultar_sem_imagem),
            "ocultar_servicos": bool(tenant.ecommerce_ocultar_servicos),
        },
        "resumo": summary,
        "total": total,
        "offset": offset,
        "limit": limit,
        "itens": filtered[offset : offset + limit],
    }


@router.get("/demanda")
@require_any_permission(_ANALYTICS_PERMISSIONS)
def get_demanda(
    dias: int = Query(default=30, ge=1, le=3650),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    rows = (
        db.query(
            EcommerceNotifyRequest.product_id,
            func.max(EcommerceNotifyRequest.product_name).label("product_name"),
            func.count(EcommerceNotifyRequest.id).label("total_pedidos"),
            func.sum(
                case((EcommerceNotifyRequest.notified.is_(False), 1), else_=0)
            ).label("pendentes"),
            func.max(Produto.codigo).label("codigo"),
            func.max(Produto.estoque_atual).label("estoque_atual"),
        )
        .outerjoin(
            Produto,
            and_(
                Produto.id == EcommerceNotifyRequest.product_id,
                Produto.tenant_id == tenant_id,
            ),
        )
        .filter(
            EcommerceNotifyRequest.tenant_id == tenant_id,
            EcommerceNotifyRequest.created_at >= _period_start(dias),
        )
        .group_by(EcommerceNotifyRequest.product_id)
        .order_by(func.count(EcommerceNotifyRequest.id).desc())
        .limit(20)
        .all()
    )
    return [
        {
            "product_id": row.product_id,
            "product_name": row.product_name,
            "codigo": row.codigo,
            "estoque_atual": float(row.estoque_atual or 0),
            "total_pedidos": int(row.total_pedidos or 0),
            "pendentes": int(row.pendentes or 0),
        }
        for row in rows
    ]


@router.get("/mais-vendidos")
@require_any_permission(_ANALYTICS_PERMISSIONS)
def get_mais_vendidos(
    dias: int = Query(default=30, ge=1, le=3650),
    canal: str = Query(default="ecommerce"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    rows = (
        db.query(
            PedidoItem.produto_id,
            func.max(PedidoItem.nome).label("nome"),
            func.sum(PedidoItem.quantidade).label("total_vendido"),
            func.sum(PedidoItem.subtotal).label("receita"),
            func.count(func.distinct(PedidoItem.pedido_id)).label("qtd_pedidos"),
        )
        .join(Pedido, Pedido.pedido_id == PedidoItem.pedido_id)
        .filter(
            PedidoItem.tenant_id == tenant_id,
            *_pedido_filters(tenant_id, dias, canal),
            Pedido.status.in_(STATUS_PAGOS),
        )
        .group_by(PedidoItem.produto_id)
        .order_by(func.sum(PedidoItem.quantidade).desc())
        .limit(20)
        .all()
    )
    return [
        {
            "produto_id": row.produto_id,
            "nome": row.nome,
            "total_vendido": float(row.total_vendido or 0),
            "receita": round(float(row.receita or 0), 2),
            "qtd_pedidos": int(row.qtd_pedidos or 0),
        }
        for row in rows
    ]


@router.get("/pedidos-recentes")
@require_any_permission(_ANALYTICS_PERMISSIONS)
def get_pedidos_recentes(
    dias: int = Query(default=30, ge=1, le=3650),
    canal: str = Query(default="ecommerce"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    rows = (
        db.query(
            Pedido.pedido_id,
            Pedido.status,
            Pedido.total,
            Pedido.created_at,
            Pedido.origem,
            func.coalesce(func.sum(PedidoItem.quantidade), 0).label("qtd_itens"),
        )
        .outerjoin(
            PedidoItem,
            and_(
                PedidoItem.pedido_id == Pedido.pedido_id,
                PedidoItem.tenant_id == tenant_id,
            ),
        )
        .filter(
            *_pedido_filters(tenant_id, dias, canal),
            Pedido.status.in_(STATUS_PAGOS),
        )
        .group_by(
            Pedido.id,
            Pedido.pedido_id,
            Pedido.status,
            Pedido.total,
            Pedido.created_at,
            Pedido.origem,
        )
        .order_by(Pedido.created_at.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "pedido_id": row.pedido_id,
            "status": row.status,
            "total": round(float(row.total or 0), 2),
            "qtd_itens": int(row.qtd_itens or 0),
            "origem": row.origem,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
