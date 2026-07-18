from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import case, func, select

from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada


def construir_contagem_entregas(tenant_id):
    paradas_por_rota = (
        select(
            RotaEntregaParada.rota_id.label("rota_id"),
            func.count(RotaEntregaParada.id).label("quantidade"),
        )
        .where(RotaEntregaParada.tenant_id == tenant_id)
        .group_by(RotaEntregaParada.rota_id)
        .subquery()
    )
    quantidade = case(
        (
            func.coalesce(paradas_por_rota.c.quantidade, 0) > 0,
            paradas_por_rota.c.quantidade,
        ),
        (RotaEntrega.venda_id.isnot(None), 1),
        else_=0,
    )
    return paradas_por_rota, quantidade


def juntar_contagem_entregas(query, paradas_por_rota):
    return query.outerjoin(
        paradas_por_rota, paradas_por_rota.c.rota_id == RotaEntrega.id
    )


def filtrar_periodo_conclusao(query, data_inicio: date, data_fim: date):
    inicio = datetime.combine(data_inicio, time.min)
    fim_exclusivo = datetime.combine(data_fim + timedelta(days=1), time.min)
    return query.filter(
        RotaEntrega.data_conclusao >= inicio,
        RotaEntrega.data_conclusao < fim_exclusivo,
    )


def calcular_medias_por_entrega(
    total_entregas,
    custo_total,
    taxa_total,
) -> tuple[float, float]:
    quantidade = int(total_entregas or 0)
    if quantidade <= 0:
        return 0.0, 0.0
    divisor = Decimal(quantidade)
    custo_medio = Decimal(str(custo_total or 0)) / divisor
    taxa_media = Decimal(str(taxa_total or 0)) / divisor
    return float(custo_medio), float(taxa_media)
