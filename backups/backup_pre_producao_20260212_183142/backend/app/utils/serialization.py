"""
Utilitários de serialização segura para conversão de tipos
Evita TypeErrors comuns com Decimal, datetime, None, etc.
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Optional, Any


def safe_decimal_to_float(value: Optional[Decimal]) -> Optional[float]:
    """
    Converte Decimal para float de forma segura.
    
    Args:
        value: Valor Decimal ou None
        
    Returns:
        float se valor válido, None se None
        
    Examples:
        >>> safe_decimal_to_float(Decimal("10.50"))
        10.5
        >>> safe_decimal_to_float(None)
        None
        >>> safe_decimal_to_float(Decimal("0"))
        0.0
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    # Se já é float/int, retorna convertido
    return float(value)


def safe_decimal_to_float_zero(value: Optional[Decimal]) -> float:
    """
    Converte Decimal para float, retornando 0.0 se None.
    Útil para campos que nunca devem ser None no JSON.
    
    Args:
        value: Valor Decimal ou None
        
    Returns:
        float (0.0 se None)
        
    Examples:
        >>> safe_decimal_to_float_zero(Decimal("10.50"))
        10.5
        >>> safe_decimal_to_float_zero(None)
        0.0
    """
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def safe_datetime_to_iso(value: Optional[datetime]) -> Optional[str]:
    """
    Converte datetime para string ISO 8601 de forma segura.
    
    Args:
        value: Valor datetime ou None
        
    Returns:
        String ISO ou None
        
    Examples:
        >>> safe_datetime_to_iso(datetime(2026, 1, 22, 15, 30))
        '2026-01-22T15:30:00'
        >>> safe_datetime_to_iso(None)
        None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def safe_int(value: Any) -> Optional[int]:
    """
    Converte para int de forma segura.
    
    Args:
        value: Qualquer valor
        
    Returns:
        int ou None
    """
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_str(value: Any) -> Optional[str]:
    """
    Converte para string de forma segura.
    
    Args:
        value: Qualquer valor
        
    Returns:
        str ou None
    """
    if value is None:
        return None
    return str(value)


def safe_bool(value: Any) -> bool:
    """
    Converte para bool de forma segura.
    
    Args:
        value: Qualquer valor
        
    Returns:
        bool (False se None)
    """
    if value is None:
        return False
    return bool(value)
