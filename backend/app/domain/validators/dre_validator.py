from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.financeiro_models import CategoriaFinanceira
from app.dre_plano_contas_models import DRESubcategoria


def validar_categoria_financeira_dre(
    db: Session,
    *,
    categoria_financeira_id: int,
    dre_subcategoria_id: int | None,
    tenant_id
) -> None:
    """
    Garante que a DRESubcategoria pertence ao mesmo tenant
    da CategoriaFinanceira.
    """

    if dre_subcategoria_id is None:
        return

    subcategoria = (
        db.query(DRESubcategoria)
        .filter(
            DRESubcategoria.id == dre_subcategoria_id,
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.ativo.is_(True),
        )
        .first()
    )

    if not subcategoria:
        raise HTTPException(
            status_code=400,
            detail="Subcategoria DRE inválida ou não pertence a este tenant."
        )

    categoria = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.id == categoria_financeira_id,
            CategoriaFinanceira.tenant_id == tenant_id,
        )
        .first()
    )

    if not categoria:
        raise HTTPException(
            status_code=400,
            detail="Categoria financeira inválida ou não pertence a este tenant."
        )
