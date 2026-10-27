"""Status canônico sem reescrever o histórico dos recebimentos antigos."""

from decimal import Decimal


def status_conta_receber(conta):
    status = str(conta.status or "pendente").strip().lower()
    if status in {"cancelado", "cancelada"}:
        return "cancelado"
    saldo = Decimal(str(conta.valor_final or 0)) - Decimal(
        str(conta.valor_recebido or 0)
    )
    if saldo <= Decimal("0.00"):
        return "recebido"
    if status == "pago":
        return "recebido"
    if status == "baixa_parcial":
        return "parcial"
    return status
