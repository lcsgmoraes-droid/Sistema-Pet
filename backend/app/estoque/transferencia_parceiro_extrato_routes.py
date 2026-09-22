"""Rota do extrato unificado de transferencias para parceiros."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.estoque.transferencia_parceiro_devolucao_service import (
    buscar_resumos_devolucao,
)
from app.estoque.transferencia_parceiro_documents import (
    _status_transferencia_parceiro,
)
from app.estoque.transferencia_parceiro_extrato_schemas import (
    TransferenciaParceiroExtratoResponse,
)
from app.estoque.transferencia_parceiro_extrato_service import (
    montar_extrato_transferencia_parceiro,
)
from app.estoque.transferencia_parceiro_support import (
    _listar_itens_por_conta_transferencia_parceiro,
)
from app.financeiro.models_contas import ContaReceber, Recebimento
from app.security.permissions_decorator import require_permission

router = APIRouter(tags=["Estoque - Transferencia Parceiro"])


@router.get(
    "/transferencia-parceiro/extrato",
    response_model=TransferenciaParceiroExtratoResponse,
)
@require_permission("produtos.visualizar")
def obter_extrato_transferencia_parceiro(
    parceiro_id: int,
    status_filtro: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista dividas e creditos da pessoa em ordem de conta-corrente."""
    _current_user, tenant_id = user_and_tenant
    contas = (
        db.query(ContaReceber)
        .options(
            joinedload(ContaReceber.cliente),
            joinedload(ContaReceber.recebimentos).joinedload(
                Recebimento.forma_pagamento
            ),
        )
        .filter(
            ContaReceber.tenant_id == str(tenant_id),
            ContaReceber.canal == "transferencia_parceiro",
            ContaReceber.cliente_id == parceiro_id,
        )
        .order_by(ContaReceber.data_emissao.asc(), ContaReceber.id.asc())
        .all()
    )

    status_normalizado = (status_filtro or "").strip().lower()
    if status_normalizado:
        contas = [
            conta
            for conta in contas
            if _status_transferencia_parceiro(conta)[0] == status_normalizado
        ]

    conta_ids = [int(conta.id) for conta in contas]
    itens_por_conta = _listar_itens_por_conta_transferencia_parceiro(
        db, tenant_id, conta_ids
    )
    resumos_devolucao = buscar_resumos_devolucao(
        db, tenant_id=tenant_id, conta_ids=conta_ids
    )
    return montar_extrato_transferencia_parceiro(
        parceiro_id=parceiro_id,
        contas=contas,
        itens_por_conta=itens_por_conta,
        resumos_devolucao=resumos_devolucao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
