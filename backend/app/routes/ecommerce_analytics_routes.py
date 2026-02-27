"""Rotas de Analytics do E-commerce."""
import json
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Tenant
from app.pedido_models import Pedido, PedidoItem
from app.routes.ecommerce_notify_routes import EcommerceNotifyRequest

router = APIRouter(prefix="/ecommerce-analytics", tags=["ecommerce-analytics"])


@router.get("/resumo")
def get_resumo(
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = current_user_and_tenant
    tid = str(tenant_id)

    # Pedidos finalizados do e-commerce (somente pagos/aprovados — exclui criado, cancelado, expirado, carrinho)
    ORIGENS_ECOMMERCE = ("web", "app", "marketplace", "ecommerce")
    STATUS_PAGOS = ("aprovado", "finalizado", "pago")
    pedidos_validos = (
        db.query(Pedido)
        .filter(
            Pedido.tenant_id == tid,
            Pedido.status.in_(STATUS_PAGOS),
            Pedido.origem.in_(ORIGENS_ECOMMERCE),
        )
        .all()
    )
    total_pedidos = len(pedidos_validos)
    receita_total = sum(float(p.total or 0) for p in pedidos_validos)
    ticket_medio = receita_total / total_pedidos if total_pedidos > 0 else 0

    # Pedidos hoje
    hoje_inicio = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    pedidos_hoje = sum(
        1 for p in pedidos_validos
        if p.created_at and p.created_at >= hoje_inicio
    )

    # Carrinhos abandonados (status = 'carrinho', criados há mais de 1 hora, só e-commerce)
    uma_hora_atras = datetime.now(timezone.utc) - timedelta(hours=1)
    carrinhos_abandonados = (
        db.query(Pedido)
        .filter(
            Pedido.tenant_id == tid,
            Pedido.status == "carrinho",
            Pedido.created_at <= uma_hora_atras,
            Pedido.origem.in_(ORIGENS_ECOMMERCE),
        )
        .count()
    )

    # Avise-me pendentes
    avise_me_pendentes = (
        db.query(func.count(EcommerceNotifyRequest.id))
        .filter(
            EcommerceNotifyRequest.tenant_id == tid,
            EcommerceNotifyRequest.notified == False,
        )
        .scalar()
        or 0
    )

    # Pedidos por status (apenas e-commerce)
    status_counts = (
        db.query(Pedido.status, func.count(Pedido.id))
        .filter(Pedido.tenant_id == tid, Pedido.origem.in_(("web", "app", "marketplace", "ecommerce")))
        .group_by(Pedido.status)
        .all()
    )

    return {
        "total_pedidos": total_pedidos,
        "receita_total": round(receita_total, 2),
        "ticket_medio": round(ticket_medio, 2),
        "pedidos_hoje": pedidos_hoje,
        "carrinhos_abandonados": carrinhos_abandonados,
        "avise_me_pendentes": avise_me_pendentes,
        "pedidos_por_status": {s: c for s, c in status_counts},
    }


@router.get("/demanda")
def get_demanda(
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Produtos com mais pedidos de avise-me pendentes = demanda reprimida."""
    _, tenant_id = current_user_and_tenant
    tid = str(tenant_id)

    rows = (
        db.query(
            EcommerceNotifyRequest.product_id,
            EcommerceNotifyRequest.product_name,
            func.count(EcommerceNotifyRequest.id).label("total_pedidos"),
            func.count(
                EcommerceNotifyRequest.id.distinct()
                if not EcommerceNotifyRequest.notified
                else None
            ).label("pendentes"),
        )
        .filter(EcommerceNotifyRequest.tenant_id == tid)
        .group_by(EcommerceNotifyRequest.product_id, EcommerceNotifyRequest.product_name)
        .order_by(func.count(EcommerceNotifyRequest.id).desc())
        .limit(20)
        .all()
    )

    # Buscar codigo (SKU) dos produtos
    from app.produtos_models import Produto
    result = []
    for row in rows:
        pendentes = (
            db.query(func.count(EcommerceNotifyRequest.id))
            .filter(
                EcommerceNotifyRequest.tenant_id == tid,
                EcommerceNotifyRequest.product_id == row.product_id,
                EcommerceNotifyRequest.notified == False,
            )
            .scalar() or 0
        )
        prod = db.query(Produto).filter(Produto.id == row.product_id).first()
        result.append({
            "product_id": row.product_id,
            "product_name": row.product_name,
            "codigo": prod.codigo if prod else None,
            "estoque_atual": float(prod.estoque_atual or 0) if prod else 0,
            "total_pedidos": row.total_pedidos,
            "pendentes": pendentes,
        })

    return result


@router.get("/mais-vendidos")
def get_mais_vendidos(
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Produtos mais vendidos no e-commerce pela quantidade em pedidos."""
    _, tenant_id = current_user_and_tenant
    tid = str(tenant_id)

    rows = (
        db.query(
            PedidoItem.produto_id,
            func.max(PedidoItem.nome).label("nome"),
            func.sum(PedidoItem.quantidade).label("total_vendido"),
            func.sum(PedidoItem.subtotal).label("receita"),
            func.count(PedidoItem.id.distinct()).label("qtd_pedidos"),
        )
        .join(Pedido, Pedido.pedido_id == PedidoItem.pedido_id)
        .filter(
            PedidoItem.tenant_id == tid,
            Pedido.tenant_id == tid,
            Pedido.status.in_(("aprovado", "finalizado", "pago")),
            Pedido.origem.in_(("web", "app", "marketplace", "ecommerce")),
        )
        .group_by(PedidoItem.produto_id)
        .order_by(func.sum(PedidoItem.quantidade).desc())
        .limit(20)
        .all()
    )

    return [
        {
            "produto_id": r.produto_id,
            "nome": r.nome,
            "total_vendido": float(r.total_vendido or 0),
            "receita": round(float(r.receita or 0), 2),
            "qtd_pedidos": r.qtd_pedidos,
        }
        for r in rows
    ]


@router.get("/pedidos-recentes")
def get_pedidos_recentes(
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Últimos 30 pedidos do e-commerce."""
    _, tenant_id = current_user_and_tenant
    tid = str(tenant_id)

    pedidos = (
        db.query(Pedido)
        .filter(
            Pedido.tenant_id == tid,
            Pedido.status.in_(("aprovado", "finalizado", "pago")),
            Pedido.origem.in_(("web", "app", "marketplace", "ecommerce")),
        )
        .order_by(Pedido.created_at.desc())
        .limit(30)
        .all()
    )

    result = []
    for p in pedidos:
        itens = (
            db.query(PedidoItem)
            .filter(PedidoItem.pedido_id == p.pedido_id)
            .all()
        )
        result.append({
            "pedido_id": p.pedido_id,
            "status": p.status,
            "total": round(float(p.total or 0), 2),
            "qtd_itens": sum(int(i.quantidade or 0) for i in itens),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return result


@router.get("/ga-data")
def get_ga_data(
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Busca dados de comportamento do Google Analytics 4 (sessões, páginas, etc)."""
    import base64
    credentials_b64 = os.environ.get("GA4_CREDENTIALS_B64", "")
    property_id = os.environ.get("GA4_PROPERTY_ID", "526330617")

    if not credentials_b64:
        return {"disponivel": False, "motivo": "Credenciais GA4 não configuradas"}

    try:
        credentials_json = base64.b64decode(credentials_b64).decode("utf-8")
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )
        from google.oauth2 import service_account

        # Carrega as credenciais do JSON armazenado na variável de ambiente
        creds_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=credentials)

        # Relatório principal: métricas gerais dos últimos 30 dias
        request_geral = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="activeUsers"),
                Metric(name="screenPageViews"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
            ],
        )
        resp_geral = client.run_report(request_geral)
        row = resp_geral.rows[0].metric_values if resp_geral.rows else None

        sessoes = int(row[0].value) if row else 0
        usuarios_ativos = int(row[1].value) if row else 0
        page_views = int(row[2].value) if row else 0
        bounce_rate = round(float(row[3].value) * 100, 1) if row else 0
        duracao_media_seg = round(float(row[4].value)) if row else 0

        # Top 5 páginas mais visitadas
        request_paginas = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            dimensions=[Dimension(name="pagePath")],
            metrics=[Metric(name="screenPageViews")],
            limit=5,
        )
        resp_paginas = client.run_report(request_paginas)
        top_paginas = [
            {
                "pagina": r.dimension_values[0].value,
                "visualizacoes": int(r.metric_values[0].value),
            }
            for r in resp_paginas.rows
        ]

        # Visitantes por dia (últimos 30 dias) para o gráfico
        request_diario = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            dimensions=[Dimension(name="date")],
            metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
            order_bys=[{"dimension": {"dimension_name": "date"}}],
        )
        resp_diario = client.run_report(request_diario)
        visitantes_por_dia = [
            {
                "data": r.dimension_values[0].value,  # formato YYYYMMDD
                "sessoes": int(r.metric_values[0].value),
                "usuarios": int(r.metric_values[1].value),
            }
            for r in resp_diario.rows
        ]

        # Formata duração em minutos e segundos
        minutos = duracao_media_seg // 60
        segundos = duracao_media_seg % 60
        duracao_formatada = f"{minutos}m {segundos}s"

        return {
            "disponivel": True,
            "periodo": "últimos 30 dias",
            "sessoes": sessoes,
            "usuarios_ativos": usuarios_ativos,
            "page_views": page_views,
            "bounce_rate": bounce_rate,
            "duracao_media": duracao_formatada,
            "top_paginas": top_paginas,
            "visitantes_por_dia": visitantes_por_dia,
        }

    except Exception as e:
        return {"disponivel": False, "motivo": f"Erro ao consultar GA4: {str(e)}"}
