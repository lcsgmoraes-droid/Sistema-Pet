"""Rotas de entrada/divida de parceiro."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.estoque.transferencia_parceiro_entrada_service import (
    listar_entradas_parceiro,
    registrar_entrada_parceiro,
)
from app.estoque.transferencia_parceiro_schemas import (
    TransferenciaParceiroEntradaHistoricoResponse,
    TransferenciaParceiroEntradaRequest,
    TransferenciaParceiroEntradaResponse,
)
from app.security.permissions_decorator import require_permission


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Estoque - Transferencia Parceiro"])


@router.get(
    "/transferencia-parceiro/entrada-parceiro/historico",
    response_model=TransferenciaParceiroEntradaHistoricoResponse,
)
@require_permission("produtos.visualizar")
def listar_entradas_de_parceiro(
    page: int = 1,
    page_size: int = 20,
    parceiro_id: int | None = None,
    status_filtro: str | None = None,
    busca: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista dividas de entradas recebidas de parceiros."""
    _current_user, tenant_id = user_and_tenant
    return listar_entradas_parceiro(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        parceiro_id=parceiro_id,
        status_filtro=status_filtro,
        busca=busca,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


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
