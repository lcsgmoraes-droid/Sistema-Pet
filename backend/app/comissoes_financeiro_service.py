"""Integração financeira do ciclo de vida das comissões."""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from app.financeiro_models import ContaPagar, Pagamento
from app.utils.tenant_safe_sql import execute_tenant_safe


def cancelar_provisoes_comissao_venda(
    db: Session,
    *,
    venda_id: int,
    tenant_id,
    motivo: str,
) -> dict:
    """Cancela contas não pagas e reverte a despesa de competência no DRE."""
    ids_vinculados = {
        row[0]
        for row in execute_tenant_safe(
            db,
            """
            SELECT DISTINCT conta_pagar_id
            FROM comissoes_itens
            WHERE venda_id = :venda_id
              AND conta_pagar_id IS NOT NULL
              AND {tenant_filter}
            """,
            {"venda_id": venda_id},
            tenant_id=tenant_id,
        ).fetchall()
    }
    inconsistentes = execute_tenant_safe(
        db,
        """
        SELECT COUNT(*)
        FROM comissoes_itens
        WHERE venda_id = :venda_id
          AND COALESCE(comissao_provisionada, false) = true
          AND conta_pagar_id IS NULL
          AND {tenant_filter}
        """,
        {"venda_id": venda_id},
        tenant_id=tenant_id,
    ).scalar()
    if inconsistentes:
        raise HTTPException(
            status_code=409,
            detail=(
                "A venda possui comissão marcada como provisionada, mas sem conta a pagar. "
                "Faça a conciliação financeira antes de cancelar ou reabrir."
            ),
        )

    filtros = [ContaPagar.documento.like(f"COMISSAO-VENDA-{venda_id}-%")]
    if ids_vinculados:
        filtros.append(ContaPagar.id.in_(ids_vinculados))

    contas = (
        db.query(ContaPagar)
        .filter(ContaPagar.tenant_id == tenant_id, or_(*filtros))
        .with_for_update()
        .all()
    )

    contas_ativas = [conta for conta in contas if conta.status != "cancelado"]
    contas_pagas = []
    for conta in contas_ativas:
        tem_pagamento = (
            db.query(Pagamento.id)
            .filter(
                Pagamento.conta_pagar_id == conta.id,
                Pagamento.tenant_id == tenant_id,
            )
            .first()
            is not None
        )
        if (
            conta.status in {"pago", "parcial"}
            or Decimal(str(conta.valor_pago or 0)) > 0
            or tem_pagamento
        ):
            contas_pagas.append(conta.id)

    if contas_pagas:
        raise HTTPException(
            status_code=409,
            detail=(
                "A venda possui comissão já paga ou parcialmente paga nas contas "
                + ", ".join(str(conta_id) for conta_id in contas_pagas)
                + ". Estorne o pagamento antes de cancelar ou reabrir a venda."
            ),
        )

    valor_revertido = Decimal("0")
    for conta in contas_ativas:
        valor = Decimal(str(conta.valor_original or 0))
        if conta.dre_subcategoria_id and conta.canal and conta.data_emissao and valor:
            atualizar_dre_por_lancamento(
                db=db,
                tenant_id=tenant_id,
                dre_subcategoria_id=conta.dre_subcategoria_id,
                canal=conta.canal,
                valor=-valor,
                data_lancamento=conta.data_emissao,
                tipo_movimentacao="ESTORNO_DESPESA",
                commit=False,
            )
            valor_revertido += valor

        conta.status = "cancelado"
        complemento = f"Provisão cancelada: {motivo}"
        conta.observacoes = (
            f"{conta.observacoes}\n{complemento}" if conta.observacoes else complemento
        )

    return {
        "contas_canceladas": len(contas_ativas),
        "valor_dre_revertido": float(valor_revertido),
    }
