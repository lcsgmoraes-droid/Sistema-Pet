from sqlalchemy.orm import Session

from app.ia.aba7_models import DREPeriodo
from app.ia.aba7_dre_detalhada_models import DREDetalheCanal, DREConsolidado
from app.dre_plano_contas_models import DRESubcategoria


def montar_contexto_dre_ia(
    db: Session,
    *,
    periodo_id: int,
    tenant_id,
) -> dict:
    """
    Retorna o contexto estruturado da DRE
    para consumo por LLM (IA generativa).
    """

    periodo = (
        db.query(DREPeriodo)
        .filter(
            DREPeriodo.id == periodo_id,
            DREPeriodo.tenant_id == tenant_id,
        )
        .first()
    )

    canais = (
        db.query(DREDetalheCanal)
        .filter(
            DREDetalheCanal.periodo_id == periodo_id,
            DREDetalheCanal.tenant_id == tenant_id,
        )
        .all()
    )

    consolidado = (
        db.query(DREConsolidado)
        .filter(
            DREConsolidado.periodo_id == periodo_id,
            DREConsolidado.tenant_id == tenant_id,
        )
        .first()
    )

    subcategorias = (
        db.query(DRESubcategoria)
        .filter(
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.ativo.is_(True),
        )
        .all()
    )

    return {
        "periodo": {
            "id": periodo.id,
            "ano": periodo.ano,
            "mes": periodo.mes,
            "fechado": periodo.fechado,
        },
        "consolidado": consolidado.to_dict() if consolidado else None,
        "canais": [c.to_dict() for c in canais],
        "subcategorias": [
            {
                "id": s.id,
                "nome": s.nome,
                "tipo_custo": s.tipo_custo.value,
                "base_rateio": s.base_rateio.value if s.base_rateio else None,
                "escopo_rateio": s.escopo_rateio.value,
            }
            for s in subcategorias
        ],
    }
