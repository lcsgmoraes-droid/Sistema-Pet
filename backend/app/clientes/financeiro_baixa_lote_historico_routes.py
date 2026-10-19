"""Consulta e estorno do recebimento único, sem editar vendas individualmente."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.clientes.baixas_lote_service import estornar_lote, listar_lotes
from app.db import get_session

router = APIRouter()
logger = logging.getLogger(__name__)


class EstornoLoteInput(BaseModel):
    motivo: str = Field(min_length=5, max_length=500)


@router.get("/{cliente_id}/baixas-lote")
def historico_baixas_lote(
    cliente_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    return listar_lotes(db, tenant_id, cliente_id, page, per_page)


@router.post("/{cliente_id}/baixas-lote/{lote_id}/estornar")
def estornar_baixa_lote(
    cliente_id: int,
    lote_id: int,
    dados: EstornoLoteInput,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    try:
        resultado = estornar_lote(
            db,
            tenant_id=tenant_id,
            cliente_id=cliente_id,
            lote_id=lote_id,
            current_user=user,
            motivo=dados.motivo,
        )
        db.commit()
        return resultado
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Erro ao estornar baixa em lote %s", lote_id)
        raise HTTPException(
            500, "Não foi possível estornar o lançamento. Nenhum valor foi alterado."
        )
