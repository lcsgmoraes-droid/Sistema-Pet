"""Rotas agregadoras do relatorio de vendas."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .relatorio_vendas_builder import montar_relatorio_vendas
from .relatorio_vendas_common import _normalizar_canal_venda_relatorio
from .relatorio_vendas_pdf import exportar_vendas_pdf as exportar_vendas_pdf
from .relatorio_vendas_pdf import router as relatorio_vendas_pdf_router
from .services.venda_rentabilidade_reprocessamento_service import (
    reprocessar_rentabilidade_vendas,
)


router = APIRouter(prefix="/relatorios")
router.include_router(relatorio_vendas_pdf_router)


class ReprocessarRentabilidadeVendasRequest(BaseModel):
    venda_ids: Optional[list[int]] = Field(
        default=None, description="IDs das vendas selecionadas"
    )
    data_inicio: Optional[str] = Field(
        default=None, description="Data inicial YYYY-MM-DD"
    )
    data_fim: Optional[str] = Field(default=None, description="Data final YYYY-MM-DD")
    canal_venda: Optional[str] = Field(
        default=None, description="Canal de venda opcional"
    )


class ReprocessarRentabilidadeVendasResponse(BaseModel):
    total_encontrado: int
    total_reprocessado: int
    vendas: list[dict]


@router.get("/vendas/relatorio")
async def obter_relatorio_vendas(
    data_inicio: Optional[str] = Query(None),
    data_fim: Optional[str] = Query(None),
    canal_venda: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna o relatorio completo de vendas do periodo."""
    _current_user, tenant_id = user_and_tenant
    return montar_relatorio_vendas(
        data_inicio=data_inicio,
        data_fim=data_fim,
        canal_venda=canal_venda,
        db=db,
        tenant_id=tenant_id,
    )


@router.post(
    "/vendas/reprocessar-rentabilidade",
    response_model=ReprocessarRentabilidadeVendasResponse,
)
async def reprocessar_rentabilidade_relatorio_vendas(
    payload: ReprocessarRentabilidadeVendasRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Reprocessa manualmente a rentabilidade de vendas usando o custo atual dos produtos."""
    _current_user, tenant_id = user_and_tenant
    venda_ids = payload.venda_ids or []
    tem_ids = any(int(venda_id or 0) > 0 for venda_id in venda_ids)
    tem_periodo = bool(payload.data_inicio and payload.data_fim)

    if not tem_ids and not tem_periodo:
        raise HTTPException(
            status_code=400,
            detail="Informe vendas selecionadas ou um periodo completo para reprocessar.",
        )

    resultado = reprocessar_rentabilidade_vendas(
        db,
        tenant_id=tenant_id,
        venda_ids=venda_ids if tem_ids else None,
        data_inicio=payload.data_inicio if not tem_ids else None,
        data_fim=payload.data_fim if not tem_ids else None,
        canal_venda=_normalizar_canal_venda_relatorio(payload.canal_venda),
    )
    db.commit()
    return resultado
