"""Normalizacao de datas operacionais do Banho & Tosa."""

from datetime import datetime
from typing import Optional


def normalizar_data_operacional(valor: Optional[datetime]) -> Optional[datetime]:
    """Remove timezone antes de comparar horarios operacionais exibidos na agenda."""
    if valor is None or valor.tzinfo is None:
        return valor
    return valor.replace(tzinfo=None)
