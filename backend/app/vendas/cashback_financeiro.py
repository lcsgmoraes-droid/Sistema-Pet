"""Ajustes financeiros quando o pagamento com cashback é estornado."""

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.campaigns.models import CashbackSourceTypeEnum, CashbackTransaction
from app.financeiro_models import LancamentoManual
from app.vendas_models import VendaPagamento


def cancelar_despesas_cashback_venda(
    db: Session, *, tenant_id, numero_venda: str
) -> int:
    """Cancela a despesa automática criada para o resgate desta venda."""
    lancamentos = (
        db.query(LancamentoManual)
        .filter(
            LancamentoManual.tenant_id == tenant_id,
            LancamentoManual.documento == f"CASHBACK-{numero_venda}",
            LancamentoManual.tipo == "saida",
            LancamentoManual.gerado_automaticamente.is_(True),
            LancamentoManual.status.in_(("previsto", "realizado")),
        )
        .all()
    )
    for lancamento in lancamentos:
        lancamento.status = "cancelado"
    return len(lancamentos)


def remover_pagamentos_cashback_venda(db: Session, *, tenant_id, venda_id: int) -> int:
    """Retira parcelas resgatadas antes de devolver o cashback ao cliente."""
    pagamentos = (
        db.query(VendaPagamento)
        .filter(
            VendaPagamento.tenant_id == tenant_id,
            VendaPagamento.venda_id == venda_id,
            func.lower(func.trim(VendaPagamento.forma_pagamento)) == "cashback",
        )
        .all()
    )
    for pagamento in pagamentos:
        db.delete(pagamento)
    db.flush()
    return len(pagamentos)


def _valores_liquidos_por_resgate(
    db: Session, *, tenant_id, resgates: list[tuple[int, Decimal]]
) -> dict[int, Decimal]:
    if not resgates:
        return {}
    resgate_ids = [int(resgate_id) for resgate_id, _ in resgates]
    estornos = (
        db.query(
            CashbackTransaction.source_id,
            CashbackTransaction.amount,
            CashbackTransaction.tx_type,
        )
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.reversal,
            or_(
                CashbackTransaction.amount > 0,
                CashbackTransaction.tx_type == "closed",
            ),
            CashbackTransaction.source_id.in_(resgate_ids),
        )
        .all()
    )
    estornado_por_resgate: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    resgates_encerrados = set()
    for resgate_id, valor, tx_type in estornos:
        if tx_type == "closed":
            resgates_encerrados.add(int(resgate_id))
        estornado_por_resgate[int(resgate_id)] += Decimal(str(valor))

    liquido_por_resgate: dict[int, Decimal] = {}
    for resgate_id, valor in resgates:
        resgatado = -Decimal(str(valor))
        ainda_ativo = (
            Decimal("0.00")
            if int(resgate_id) in resgates_encerrados
            else max(
                Decimal("0.00"), resgatado - estornado_por_resgate[int(resgate_id)]
            )
        )
        liquido_por_resgate[int(resgate_id)] = ainda_ativo
    return liquido_por_resgate


def cashback_resgatado_liquido_por_transacao(
    db: Session, *, tenant_id, redemption_ids: Iterable[int]
) -> dict[int, Decimal]:
    """Retorna o valor ainda ativo de cada débito de resgate solicitado."""
    ids = sorted({int(resgate_id) for resgate_id in redemption_ids})
    if not ids:
        return {}
    resgates = (
        db.query(CashbackTransaction.id, CashbackTransaction.amount)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.redemption,
            CashbackTransaction.amount < 0,
            CashbackTransaction.id.in_(ids),
        )
        .all()
    )
    return _valores_liquidos_por_resgate(db, tenant_id=tenant_id, resgates=resgates)


def cashback_resgatado_liquido_por_venda(
    db: Session, *, tenant_id, venda_ids: Iterable[int]
) -> dict[int, Decimal]:
    """Soma resgates ainda ativos, abatendo os estornos de cada débito."""
    ids = sorted({int(venda_id) for venda_id in venda_ids})
    if not ids:
        return {}
    resgates = (
        db.query(
            CashbackTransaction.id,
            CashbackTransaction.source_id,
            CashbackTransaction.amount,
        )
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.redemption,
            CashbackTransaction.amount < 0,
            CashbackTransaction.source_id.in_(ids),
        )
        .all()
    )
    liquido_por_resgate = _valores_liquidos_por_resgate(
        db,
        tenant_id=tenant_id,
        resgates=[(row[0], row[2]) for row in resgates],
    )
    total_por_venda: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for resgate_id, venda_id, _ in resgates:
        total_por_venda[int(venda_id)] += liquido_por_resgate[int(resgate_id)]
    return dict(total_por_venda)


__all__ = [
    "cashback_resgatado_liquido_por_venda",
    "cashback_resgatado_liquido_por_transacao",
    "cancelar_despesas_cashback_venda",
    "remover_pagamentos_cashback_venda",
]
