"""
Utilitários do Sistema Pet Shop Pro
"""

from .serialization import (
    safe_decimal_to_float,
    safe_decimal_to_float_zero,
    safe_datetime_to_iso,
    safe_int,
    safe_str,
    safe_bool
)

from .logger import (
    logger,
    set_trace_id,
    get_trace_id,
    set_user_id,
    set_endpoint,
    generate_trace_id,
    clear_context
)

__all__ = [
    # Serialization
    'safe_decimal_to_float',
    'safe_decimal_to_float_zero',
    'safe_datetime_to_iso',
    'safe_int',
    'safe_str',
    'safe_bool',
    # Logger
    'logger',
    'set_trace_id',
    'get_trace_id',
    'set_user_id',
    'set_endpoint',
    'generate_trace_id',
    'clear_context'
]
