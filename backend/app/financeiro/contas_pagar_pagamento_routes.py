"""Rotas de pagamento e resumo de contas a pagar."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro.contas_pagar_common import _decimal_monetario
from app.financeiro.contas_pagar_pagamento_service import (
    aplicar_pagamento_conta_pagar,
    validar_conta_bancaria,
    validar_forma_pagamento,
)
from app.financeiro.contas_pagar_schemas import PagamentoCreate, PagamentoLoteCreate
from app.financeiro_models import ContaPagar
from app.idempotency import idempotent

router = APIRouter()


@router.post("/pagar-lote")
@idempotent()
async def registrar_pagamento_lote(
    payload: PagamentoLoteCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Baixa em lote o saldo aberto das contas selecionadas."""
    current_user, tenant_id = user_and_tenant
    contas = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.id.in_(payload.conta_ids),
        )
        .order_by(ContaPagar.id.asc())
        .all()
    )
    if len(contas) != len(payload.conta_ids):
        encontradas = {conta.id for conta in contas}
        faltantes = [item for item in payload.conta_ids if item not in encontradas]
        raise HTTPException(
            status_code=404,
            detail=f"Conta(s) nao encontrada(s): {', '.join(map(str, faltantes))}",
        )

    forma_pagamento_validada_id = validar_forma_pagamento(
        db,
        tenant_id=tenant_id,
        forma_pagamento_id=payload.forma_pagamento_id,
    )
    conta_bancaria = validar_conta_bancaria(
        db,
        tenant_id=tenant_id,
        conta_bancaria_id=payload.conta_bancaria_id,
    )

    resultados = []
    valor_total_pago = _decimal_monetario(0)
    for conta in contas:
        resultado = aplicar_pagamento_conta_pagar(
            db,
            conta=conta,
            tenant_id=tenant_id,
            current_user=current_user,
            data_pagamento=payload.data_pagamento,
            forma_pagamento_validada_id=forma_pagamento_validada_id,
            conta_bancaria=conta_bancaria,
            observacoes=payload.observacoes,
        )
        resultados.append(resultado)
        valor_total_pago += resultado["valor_pago"]

    db.commit()
    return {
        "ok": True,
        "message": "Pagamentos registrados com sucesso",
        "pagamentos_registrados": len(resultados),
        "valor_total_pago": float(valor_total_pago),
        "contas": [
            {
                "conta_id": item["conta_id"],
                "status": item["status"],
                "valor_pago": float(item["valor_pago"]),
                "saldo_restante": float(item["saldo_restante"]),
            }
            for item in resultados
        ],
    }


@router.post("/{conta_id}/pagar")
@idempotent()
async def registrar_pagamento(
    conta_id: int,
    pagamento: PagamentoCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Registra um pagamento (baixa) de conta a pagar."""
    current_user, tenant_id = user_and_tenant
    conta = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.id == conta_id,
            ContaPagar.tenant_id == tenant_id,
        )
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Conta nao encontrada")

    forma_pagamento_validada_id = validar_forma_pagamento(
        db,
        tenant_id=tenant_id,
        forma_pagamento_id=pagamento.forma_pagamento_id,
    )
    conta_bancaria = validar_conta_bancaria(
        db,
        tenant_id=tenant_id,
        conta_bancaria_id=pagamento.conta_bancaria_id,
    )
    resultado = aplicar_pagamento_conta_pagar(
        db,
        conta=conta,
        tenant_id=tenant_id,
        current_user=current_user,
        data_pagamento=pagamento.data_pagamento,
        forma_pagamento_validada_id=forma_pagamento_validada_id,
        conta_bancaria=conta_bancaria,
        observacoes=pagamento.observacoes,
        valor_base_pagamento=pagamento.valor_pago,
        valor_juros=pagamento.valor_juros,
        valor_multa=pagamento.valor_multa,
        valor_desconto=pagamento.valor_desconto,
    )
    db.commit()

    return {
        "message": "Pagamento registrado com sucesso",
        "conta_id": conta.id,
        "status": conta.status,
        "valor_pago_total": float(conta.valor_pago),
        "valor_final": float(conta.valor_final),
        "saldo_restante": float(conta.valor_final - conta.valor_pago),
        "recorrencias_criadas": resultado["recorrencias_criadas"],
    }


@router.get("/dashboard/resumo")
def dashboard_contas_pagar(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Resumo financeiro de contas a pagar."""
    _, tenant_id = user_and_tenant
    hoje = date.today()

    total_pendente = (
        db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.status.in_(["pendente", "parcial", "vencido"]),
        )
        .scalar()
        or 0
    )
    total_vencido = (
        db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status == "pendente",
                ContaPagar.data_vencimento < hoje,
            )
        )
        .scalar()
        or 0
    )
    count_vencidas = (
        db.query(func.count(ContaPagar.id))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status == "pendente",
                ContaPagar.data_vencimento < hoje,
            )
        )
        .scalar()
    )
    total_vence_hoje = (
        db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status == "pendente",
                ContaPagar.data_vencimento == hoje,
            )
        )
        .scalar()
        or 0
    )
    data_7dias = hoje + timedelta(days=7)
    total_7dias = (
        db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status == "pendente",
                ContaPagar.data_vencimento.between(hoje, data_7dias),
            )
        )
        .scalar()
        or 0
    )
    data_30dias = hoje + timedelta(days=30)
    total_30dias = (
        db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status == "pendente",
                ContaPagar.data_vencimento.between(hoje, data_30dias),
            )
        )
        .scalar()
        or 0
    )
    primeiro_dia_mes = hoje.replace(day=1)
    total_pago_mes = (
        db.query(func.sum(ContaPagar.valor_pago))
        .filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.data_pagamento >= primeiro_dia_mes,
                ContaPagar.data_pagamento <= hoje,
            )
        )
        .scalar()
        or 0
    )

    return {
        "total_pendente": float(total_pendente),
        "vencidas": {"total": float(total_vencido), "quantidade": count_vencidas},
        "vence_hoje": float(total_vence_hoje),
        "proximos_7_dias": float(total_7dias),
        "proximos_30_dias": float(total_30dias),
        "pago_mes_atual": float(total_pago_mes),
    }
