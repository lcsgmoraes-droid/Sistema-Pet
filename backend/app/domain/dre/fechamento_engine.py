from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.ia.aba7_models import DREPeriodo
from app.ia.aba7_dre_detalhada_models import DREDetalheCanal, DREConsolidado


def fechar_periodo_dre(
    db: Session,
    *,
    periodo_id: int,
    tenant_id,
) -> None:
    """
    Consolida definitivamente a DRE de um período.
    Após isso, nenhum valor pode ser recalculado.
    """

    periodo = (
        db.query(DREPeriodo)
        .filter(
            DREPeriodo.id == periodo_id,
            DREPeriodo.tenant_id == tenant_id,
        )
        .first()
    )

    if not periodo:
        raise HTTPException(
            status_code=404,
            detail="Período DRE não encontrado."
        )

    if periodo.fechado:
        raise HTTPException(
            status_code=400,
            detail="Período DRE já está fechado."
        )

    canais = (
        db.query(DREDetalheCanal)
        .filter(
            DREDetalheCanal.periodo_id == periodo.id,
            DREDetalheCanal.tenant_id == tenant_id,
        )
        .all()
    )

    if not canais:
        raise HTTPException(
            status_code=400,
            detail="Não existem canais para consolidar."
        )

    consolidado = DREConsolidado(
        tenant_id=tenant_id,
        periodo_id=periodo.id,
        receita_total=sum(c.receita_total for c in canais),
        custo_total=sum(c.custo_total for c in canais),
        despesa_total=sum(c.despesa_total for c in canais),
        resultado=sum(c.resultado for c in canais),
    )

    db.add(consolidado)

    periodo.fechado = True

    db.commit()
