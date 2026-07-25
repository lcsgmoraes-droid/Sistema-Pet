"""Rotas controladas para previa e carga de custos no Bling."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_sync.schemas import SyncCustosMarcaRequest
from app.db import get_session
from app.security.permissions_decorator import require_any_permission
from app.services.bling_cost_sync_service import BlingCostSyncService

router = APIRouter()

PERMISSOES_SYNC_CUSTO_BLING = ("compras.sincronizacao_bling", "produtos.editar")


@router.post("/custos-bling/marca")
@require_any_permission(PERMISSOES_SYNC_CUSTO_BLING)
def sincronizar_custos_marca_bling(
    payload: SyncCustosMarcaRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Sem confirmar, retorna apenas a previa.
    Com confirmar, enfileira os custos validos da marca para envio pelo worker.
    """
    _current_user, tenant_id = user_and_tenant
    try:
        result = BlingCostSyncService.preview_or_enqueue_brand(
            db,
            tenant_id=tenant_id,
            brand_name=payload.marca,
            enqueue=payload.confirmar,
        )
        if payload.confirmar:
            db.commit()
        return result
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel preparar a sincronizacao de custos com o Bling.",
        ) from error
