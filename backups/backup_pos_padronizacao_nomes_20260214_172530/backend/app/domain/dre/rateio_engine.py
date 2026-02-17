from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.dre_plano_contas_models import DRESubcategoria, TipoCusto, BaseRateio
from app.ia.aba7_models import DREPeriodo
from app.ia.aba7_dre_detalhada_models import DREDetalheCanal


def calcular_rateio_dre(
    db: Session,
    *,
    periodo: DREPeriodo,
    tenant_id,
) -> None:
    """
    Calcula rateio em tempo real para custos indiretos
    enquanto o período estiver aberto.
    """

    if periodo.fechado:
        return

    subcategorias = (
        db.query(DRESubcategoria)
        .filter(
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.tipo_custo == TipoCusto.INDIRETO_RATEAVEL,
            DRESubcategoria.ativo.is_(True),
        )
        .all()
    )

    canais = (
        db.query(DREDetalheCanal)
        .filter(
            DREDetalheCanal.tenant_id == tenant_id,
            DREDetalheCanal.periodo_id == periodo.id,
        )
        .all()
    )

    if not canais:
        raise HTTPException(
            status_code=400,
            detail="Nenhum canal encontrado para rateio."
        )

    for sub in subcategorias:

        if sub.base_rateio == BaseRateio.MANUAL:
            continue

        total_base = Decimal("0")

        for canal in canais:
            if sub.base_rateio == BaseRateio.FATURAMENTO:
                total_base += canal.faturamento
            elif sub.base_rateio == BaseRateio.PEDIDOS:
                total_base += canal.total_pedidos

        if total_base == 0:
            continue

        for canal in canais:
            if sub.base_rateio == BaseRateio.FATURAMENTO:
                proporcao = Decimal(canal.faturamento) / total_base
            elif sub.base_rateio == BaseRateio.PEDIDOS:
                proporcao = Decimal(canal.total_pedidos) / total_base
            else:
                continue

            canal.aplicar_rateio(
                subcategoria_id=sub.id,
                proporcao=proporcao
            )
