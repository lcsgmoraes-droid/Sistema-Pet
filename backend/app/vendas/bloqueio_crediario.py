"""Bloqueio opcional de vendas para clientes com crediário em atraso."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.empresa_config_geral_models import EmpresaConfigGeral
from app.financeiro_models import ContaReceber, FormaPagamento
from app.security.permissions_service import check_permission
from app.security.crediario_override import obter_vinculo_ativo
from app.audit_log import log_action


def validar_bloqueio_crediario(
    db: Session,
    tenant_id,
    cliente_id: int | None,
    *,
    venda_id: int | None = None,
    user_id: int | None = None,
    motivo_liberacao: str | None = None,
) -> None:
    if not cliente_id:
        return

    config = (
        db.query(EmpresaConfigGeral)
        .filter(EmpresaConfigGeral.tenant_id == tenant_id)
        .first()
    )
    if not config or not config.bloquear_venda_crediario_atrasado:
        return

    dias_limite = int(config.dias_atraso_bloqueio_venda or 30)
    hoje = date.today()
    conta = (
        db.query(ContaReceber)
        .join(
            FormaPagamento,
            (FormaPagamento.id == ContaReceber.forma_pagamento_id)
            & (FormaPagamento.tenant_id == tenant_id),
        )
        .filter(
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.cliente_id == cliente_id,
            FormaPagamento.tipo == "crediario",
            ContaReceber.status.in_(("pendente", "parcial", "vencido", "vencida")),
            ContaReceber.data_vencimento <= hoje - timedelta(days=dias_limite),
            (ContaReceber.valor_final - func.coalesce(ContaReceber.valor_recebido, 0))
            > Decimal("0.01"),
        )
        .order_by(ContaReceber.data_vencimento.asc())
        .first()
    )
    if conta:
        dias_atraso = (hoje - conta.data_vencimento).days
        motivo = (motivo_liberacao or "").strip()
        if motivo:
            if len(motivo) < 10:
                raise HTTPException(
                    400, "Informe um motivo com pelo menos 10 caracteres."
                )
            if user_id is None or venda_id is None:
                raise HTTPException(
                    400, "Não foi possível identificar a liberação desta venda."
                )
            vinculo = obter_vinculo_ativo(db, tenant_id, user_id)
            if not vinculo or not vinculo.pode_liberar_venda_crediario_atrasado:
                try:
                    check_permission(db, user_id, "usuarios.manage", tenant_id)
                except HTTPException as exc:
                    if exc.status_code != 403:
                        raise
                    raise HTTPException(
                        403,
                        "Este usuário não está autorizado a liberar vendas bloqueadas por crediário.",
                    ) from exc
            log_action(
                db,
                user_id,
                action="sale.overdue_credit_override",
                entity_type="vendas",
                entity_id=venda_id,
                new_value={
                    "cliente_id": cliente_id,
                    "conta_receber_id": conta.id,
                    "dias_atraso": dias_atraso,
                    "motivo": motivo,
                },
                tenant_id=tenant_id,
                commit=False,
            )
            return
        raise HTTPException(
            status_code=409,
            detail=(
                f"Venda bloqueada: o cliente tem uma parcela do crediário "
                f"em aberto há {dias_atraso} dias. Regularize o débito "
                "ou peça a um responsável para liberar esta venda."
            ),
        )
