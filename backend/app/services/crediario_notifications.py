"""Notificacoes criadas a partir das parcelas reais do crediario."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def criar_notificacoes_parcelas_crediario(
    db: Session,
    *,
    venda: Any,
    contas_ids: list[int],
    tenant_id: str,
) -> int:
    """Cria um aviso por parcela, tanto para vendas do ERP quanto do app."""
    if not contas_ids or not getattr(venda, "cliente_id", None):
        return 0

    from app.financeiro_models import ContaReceber, FormaPagamento
    from app.models import Cliente
    from app.services.app_notifications import (
        criar_notificacao_app,
        resolve_customer_app_user_id,
    )

    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == venda.cliente_id,
            Cliente.tenant_id == tenant_id,
        )
        .first()
    )
    if not cliente:
        return 0

    app_user_id = resolve_customer_app_user_id(db, tenant_id=tenant_id, cliente=cliente)
    if not app_user_id:
        return 0

    contas = (
        db.query(ContaReceber)
        .join(FormaPagamento, FormaPagamento.id == ContaReceber.forma_pagamento_id)
        .filter(
            ContaReceber.id.in_(contas_ids),
            ContaReceber.tenant_id == tenant_id,
            FormaPagamento.tenant_id == tenant_id,
            FormaPagamento.tipo == "crediario",
        )
        .order_by(ContaReceber.numero_parcela.asc(), ContaReceber.id.asc())
        .all()
    )
    criadas = 0
    numero_venda = getattr(venda, "numero_venda", None) or getattr(venda, "id", "")
    for conta in contas:
        numero = int(conta.numero_parcela or 1)
        total = int(conta.total_parcelas or 1)
        valor = float(conta.valor_final or conta.valor_original or 0)
        parcela = criar_notificacao_app(
            db,
            tenant_id=tenant_id,
            user_id=app_user_id,
            customer_id=cliente.id,
            title=f"Crediário: parcela {numero}/{total}",
            body=(
                f"A parcela {numero}/{total} da compra {numero_venda}, no valor de "
                f"R$ {valor:.2f}, vence em {conta.data_vencimento.strftime('%d/%m/%Y')}."
            ),
            source="crediario",
            kind="crediario_installment_created",
            payload={
                "source": "crediario",
                "kind": "crediario_installment_created",
                "venda_id": venda.id,
                "conta_receber_id": conta.id,
                "numero_parcela": numero,
                "total_parcelas": total,
                "data_vencimento": conta.data_vencimento.isoformat(),
                "valor": valor,
            },
            idempotency_key=f"crediario:conta:{conta.id}",
        )
        if parcela is not None:
            criadas += 1
    return criadas
