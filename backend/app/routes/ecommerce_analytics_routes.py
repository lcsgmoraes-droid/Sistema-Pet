"""Analytics operacional da loja virtual, com período e canal."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.ecommerce_analytics_models import EcommerceAnalyticsEvent
from app.models import EcommerceNotifyRequest
from app.pedido_models import Pedido, PedidoItem
from app.produtos_models import Produto
from app.security.permissions_decorator import require_any_permission

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


@router.get("/catalogo-saude")
@require_any_permission(_ANALYTICS_PERMISSIONS)
def get_catalogo_saude(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tem_imagem = or_(
        and_(
            Produto.imagem_principal.is_not(None),
            func.length(func.trim(Produto.imagem_principal)) > 0,
        ),
        Produto.imagens.any(),
    )
    tem_descricao = or_(
        and_(
            Produto.descricao_curta.is_not(None),
            func.length(func.trim(Produto.descricao_curta)) > 0,
        ),
        and_(
            Produto.descricao_completa.is_not(None),
            func.length(func.trim(Produto.descricao_completa)) > 0,
        ),
    )
    row = (
        db.query(
            func.count(Produto.id).label("publicados"),
            func.sum(
                case((func.coalesce(Produto.estoque_atual, 0) <= 0, 1), else_=0)
            ).label("sem_estoque"),
            func.sum(case((~tem_imagem, 1), else_=0)).label("sem_imagem"),
            func.sum(case((~tem_descricao, 1), else_=0)).label("sem_descricao"),
            func.sum(case((Produto.categoria_id.is_(None), 1), else_=0)).label(
                "sem_categoria"
            ),
            func.sum(case((Produto.marca_id.is_(None), 1), else_=0)).label("sem_marca"),
            func.sum(
                case(
                    (
                        func.coalesce(Produto.preco_ecommerce, Produto.preco_venda, 0)
                        <= 0,
                        1,
                    ),
                    else_=0,
                )
            ).label("sem_preco"),
        )
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
            Produto.anunciar_ecommerce.is_(True),
            Produto.tipo_produto.in_(("SIMPLES", "VARIACAO", "KIT")),
        )
        .one()
    )
    published = int(row.publicados or 0)
    problems = {
        "sem_estoque": int(row.sem_estoque or 0),
        "sem_imagem": int(row.sem_imagem or 0),
        "sem_descricao": int(row.sem_descricao or 0),
        "sem_categoria": int(row.sem_categoria or 0),
        "sem_marca": int(row.sem_marca or 0),
        "sem_preco": int(row.sem_preco or 0),
    }
    ready = (
        db.query(func.count(Produto.id))
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
            Produto.situacao.is_not(False),
            Produto.anunciar_ecommerce.is_(True),
            Produto.tipo_produto.in_(("SIMPLES", "VARIACAO", "KIT")),
            func.coalesce(Produto.estoque_atual, 0) > 0,
            tem_imagem,
            tem_descricao,
            Produto.categoria_id.is_not(None),
            Produto.marca_id.is_not(None),
            func.coalesce(Produto.preco_ecommerce, Produto.preco_venda, 0) > 0,
        )
        .scalar()
        or 0
    )
    return {
        "publicados": published,
        "prontos_para_venda": int(ready),
        "percentual_pronto": round(
            (int(ready) / published * 100) if published else 0, 2
        ),
        **problems,
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
