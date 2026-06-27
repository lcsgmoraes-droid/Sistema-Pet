"""Formatadores e helpers simples das pendencias de compras."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from .compras_pendencias_constants import UNIT_PRECISION


def _normalizar_texto(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _round_quantity(value: Any) -> float:
    try:
        decimal_value = Decimal(str(value if value is not None else 0))
    except Exception:
        decimal_value = Decimal("0")
    return float(decimal_value.quantize(UNIT_PRECISION, rounding=ROUND_HALF_UP))


def _formatar_qtd(valor: Any) -> str:
    numero = float(valor or 0)
    texto = f"{numero:.4f}".rstrip("0").rstrip(".")
    return texto or "0"


def _formatar_moeda(valor: Any) -> str:
    numero = float(valor or 0)
    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
