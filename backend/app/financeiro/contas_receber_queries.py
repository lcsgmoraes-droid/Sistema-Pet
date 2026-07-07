"""Consultas auxiliares de contas a receber."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy.orm import Session


def calcular_total_pendente_venda(venda_id: int, db: Session) -> Decimal:
    """Calcula quanto ainda falta receber de uma venda."""
    from app.financeiro_models import ContaReceber

    contas = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.venda_id == venda_id,
            ContaReceber.status.in_(["pendente", "parcial", "vencido"]),
        )
        .all()
    )

    total_pendente = Decimal("0")
    for conta in contas:
        pendente_conta = conta.valor_final - (conta.valor_recebido or Decimal("0"))
        total_pendente += pendente_conta

    return total_pendente


def listar_contas_vencidas(user_id: int, db: Session) -> List[Dict[str, Any]]:
    """Lista todas as contas vencidas de um usuario."""
    from app.financeiro_models import ContaReceber

    hoje = date.today()

    contas = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.user_id == user_id,
            ContaReceber.status.in_(["pendente", "parcial"]),
            ContaReceber.data_vencimento < hoje,
        )
        .order_by(ContaReceber.data_vencimento)
        .all()
    )

    resultado = []
    for conta in contas:
        dias_atraso = (hoje - conta.data_vencimento).days
        pendente = float(conta.valor_final) - float(conta.valor_recebido or 0)

        resultado.append(
            {
                "conta_id": conta.id,
                "descricao": conta.descricao,
                "cliente_id": conta.cliente_id,
                "valor_pendente": Decimal(str(pendente)),
                "data_vencimento": conta.data_vencimento,
                "dias_atraso": dias_atraso,
                "venda_id": conta.venda_id,
            }
        )

    return resultado
