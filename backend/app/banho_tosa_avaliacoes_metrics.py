"""Indicadores de avaliacao/NPS do Banho & Tosa."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.banho_tosa_models import BanhoTosaAvaliacao


def calcular_nps_periodo(db: Session, tenant_id, inicio: datetime, fim: datetime) -> dict:
    avaliacoes = db.query(BanhoTosaAvaliacao).filter(
        BanhoTosaAvaliacao.tenant_id == tenant_id,
        BanhoTosaAvaliacao.created_at >= inicio,
        BanhoTosaAvaliacao.created_at <= fim,
    ).all()
    return resumir_nps(avaliacoes)


def resumir_nps(avaliacoes) -> dict:
    total = len(avaliacoes)
    promotores = len([item for item in avaliacoes if item.nota_nps >= 9])
    detratores = len([item for item in avaliacoes if item.nota_nps <= 6])
    neutros = max(total - promotores - detratores, 0)
    notas_servico = [Decimal(item.nota_servico) for item in avaliacoes if item.nota_servico is not None]
    return {
        "avaliacoes": total,
        "promotores": promotores,
        "neutros": neutros,
        "detratores": detratores,
        "nps": _nps(total, promotores, detratores),
        "nota_servico_media": sum(notas_servico, Decimal("0")) / len(notas_servico) if notas_servico else Decimal("0"),
    }


def _nps(total: int, promotores: int, detratores: int) -> Decimal:
    if not total:
        return Decimal("0")
    return (Decimal(promotores) / Decimal(total) * Decimal("100")) - (Decimal(detratores) / Decimal(total) * Decimal("100"))
