"""
Utilitários para gerenciamento de timezone
Configurado para Brasília (America/Sao_Paulo) UTC-3
"""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# Timezone de Brasília
BRASILIA_TZ = ZoneInfo("America/Sao_Paulo")


def now_brasilia() -> datetime:
    """
    Retorna datetime atual no timezone de Brasília SEM timezone info.
    Isso evita conversões automáticas do banco de dados para UTC.
    
    Returns:
        datetime: Data/hora atual em Brasília (naive/sem timezone)
        
    Exemplo:
        >>> agora = now_brasilia()
        >>> print(agora)
        2026-02-13 23:26:00  # Horário de Brasília, mas sem -03:00
    """
    # Obter horário atual de Brasília
    brasilia_now = datetime.now(BRASILIA_TZ)
    # Remover timezone info para evitar conversão do banco
    return brasilia_now.replace(tzinfo=None)


def to_brasilia(dt: datetime) -> datetime:
    """
    Converte um datetime para o timezone de Brasília.
    
    Args:
        dt: Datetime para converter (pode ser naive ou com timezone)
        
    Returns:
        datetime: Data/hora convertida para Brasília
        
    Exemplo:
        >>> utc_time = datetime.utcnow()
        >>> brasilia_time = to_brasilia(utc_time)
    """
    if dt.tzinfo is None:
        # Se é naive, assume UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BRASILIA_TZ)


def format_brasilia(dt: datetime, fmt: str = "%d/%m/%Y %H:%M:%S") -> str:
    """
    Formata um datetime para string no timezone de Brasília.
    
    Args:
        dt: Datetime para formatar
        fmt: Formato de saída (padrão: dd/mm/yyyy HH:MM:SS)
        
    Returns:
        str: Data/hora formatada
        
    Exemplo:
        >>> dt = now_brasilia()
        >>> format_brasilia(dt)
        '06/02/2026 10:26:00'
    """
    brasilia_dt = to_brasilia(dt) if dt.tzinfo else dt.replace(tzinfo=BRASILIA_TZ)
    return brasilia_dt.strftime(fmt)
