"""Utilitarios pequenos compartilhados pelo PDV mobile."""

from typing import Optional


def _somente_digitos_funcionario_pdv(valor: Optional[str]) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _round_money_funcionario_pdv(valor) -> float:
    return round(float(valor or 0), 2)
