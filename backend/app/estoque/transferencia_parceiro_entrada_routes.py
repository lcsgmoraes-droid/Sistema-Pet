"""Rotas de entrada/divida de parceiro."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.estoque.transferencia_parceiro_entrada_service import (
    registrar_entrada_parceiro,
)
from app.estoque.transferencia_parceiro_schemas import (
    TransferenciaParceiroEntradaRequest,
    TransferenciaParceiroEntradaResponse,
)
from app.security.permissions_decorator import require_permission


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Estoque - Transferencia Parceiro"])


@router.post(
    "/transferencia-parceiro/entrada-parceiro",
    response_model=TransferenciaParceiroEntradaResponse,
    status_code=status.HTTP_201_CREATED,
)
@require_permission("produtos.editar")
def registrar_entrada_de_parceiro(
    payload: TransferenciaParceiroEntradaRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Registra produto recebido de parceiro, gerando conta a pagar."""
    current_user, tenant_id = user_and_tenant
    try:
        return registrar_entrada_parceiro(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            payload=payload,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao registrar entrada de parceiro: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel registrar a entrada de parceiro.",
        )
