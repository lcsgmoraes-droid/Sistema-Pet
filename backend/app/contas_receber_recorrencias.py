"""Utilitarios de recorrencia para contas a receber."""

from datetime import date, timedelta
from typing import Optional


def calcular_proxima_recorrencia(
    data_base: date, tipo_recorrencia: str, intervalo_dias: Optional[int] = None
) -> date:
    """
    Calcula a prÃ³xima data de recorrÃªncia baseado no tipo
    """
    if tipo_recorrencia == "semanal":
        return data_base + timedelta(days=7)
    elif tipo_recorrencia == "quinzenal":
        return data_base + timedelta(days=15)
    elif tipo_recorrencia == "mensal":
        # Adicionar 1 mÃªs
        mes = data_base.month + 1
        ano = data_base.year
        if mes > 12:
            mes = 1
            ano += 1
        try:
            return data_base.replace(year=ano, month=mes)
        except ValueError:
            # Caso dia nÃ£o exista no prÃ³ximo mÃªs (ex: 31 de fev), usar Ãºltimo dia do mÃªs
            import calendar

            ultimo_dia = calendar.monthrange(ano, mes)[1]
            return date(ano, mes, ultimo_dia)
    elif tipo_recorrencia == "personalizado" and intervalo_dias:
        return data_base + timedelta(days=intervalo_dias)
    else:
        raise ValueError(f"Tipo de recorrÃªncia invÃ¡lido: {tipo_recorrencia}")


# ============================================================================
# CRIAR CONTA A RECEBER
# ============================================================================
