"""Cálculo seguro e incremental de encargos para parcelas de crediário."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from .empresa_config_geral_models import EmpresaConfigGeral

CENTAVOS = Decimal("0.01")
ZERO = Decimal("0.00")
STATUS_EM_ABERTO = {"pendente", "parcial", "vencido", "vencida"}


def dinheiro(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def carregar_config_encargos(db: Session, tenant_id: int):
    return (
        db.query(EmpresaConfigGeral)
        .filter(EmpresaConfigGeral.tenant_id == tenant_id)
        .first()
    )


def conta_eh_crediario(conta) -> bool:
    forma = getattr(conta, "forma_pagamento", None)
    return str(getattr(forma, "tipo", "") or "").strip().lower() == "crediario"


def calcular_encargos_automaticos(conta, data_calculo: date, config=None) -> dict:
    """Calcula apenas os novos encargos ainda não persistidos na parcela."""
    saldo_atual = max(
        dinheiro(getattr(conta, "valor_final", 0))
        - dinheiro(getattr(conta, "valor_recebido", 0)),
        ZERO,
    )
    eh_crediario = conta_eh_crediario(conta)
    ativo = bool(config and getattr(config, "crediario_encargos_automaticos", False))
    vencimento = getattr(conta, "data_vencimento", data_calculo)
    dias_atraso = max((data_calculo - vencimento).days, 0)
    resultado = {
        "eh_crediario": eh_crediario,
        "encargos_automaticos_ativos": ativo and eh_crediario,
        "dias_atraso": dias_atraso,
        "dias_cobrados": 0,
        "valor_juros_calculado": ZERO,
        "valor_multa_calculada": ZERO,
        "saldo_atual": saldo_atual,
        "saldo_atualizado": saldo_atual,
    }

    if (
        not ativo
        or not eh_crediario
        or str(getattr(conta, "status", "")).lower() not in STATUS_EM_ABERTO
        or saldo_atual <= ZERO
    ):
        return resultado

    tolerancia = max(int(getattr(config, "dias_tolerancia_atraso", 0) or 0), 0)
    inicio_encargos = vencimento + timedelta(days=tolerancia)
    ultimo_calculo = getattr(conta, "data_ultimo_calculo_encargos", None)
    inicio_incremental = max(inicio_encargos, ultimo_calculo or inicio_encargos)
    dias_cobrados = max((data_calculo - inicio_incremental).days, 0)
    if dias_cobrados <= 0:
        return resultado

    # Encargos incidem sobre o saldo sem juros e multa já incorporados.
    base = max(
        saldo_atual
        - dinheiro(getattr(conta, "valor_juros", 0))
        - dinheiro(getattr(conta, "valor_multa", 0)),
        ZERO,
    )
    juros_mensal = Decimal(
        str(getattr(config, "crediario_juros_mensal_percentual", 0) or 0)
    )
    multa_percentual = Decimal(
        str(getattr(config, "crediario_multa_percentual", 0) or 0)
    )
    juros = dinheiro(base * juros_mensal / Decimal("100") * dias_cobrados / 30)
    multa = ZERO
    if not bool(getattr(conta, "multa_atraso_aplicada", False)):
        multa = dinheiro(base * multa_percentual / Decimal("100"))

    resultado.update(
        {
            "dias_cobrados": dias_cobrados,
            "valor_juros_calculado": juros,
            "valor_multa_calculada": multa,
            "saldo_atualizado": dinheiro(saldo_atual + juros + multa),
        }
    )
    return resultado


def aplicar_encargos_automaticos(conta, calculo: dict, data_calculo: date) -> None:
    if (
        not calculo.get("encargos_automaticos_ativos")
        or calculo.get("dias_cobrados", 0) <= 0
    ):
        return

    conta.valor_juros = dinheiro(conta.valor_juros) + dinheiro(
        calculo["valor_juros_calculado"]
    )
    conta.valor_multa = dinheiro(conta.valor_multa) + dinheiro(
        calculo["valor_multa_calculada"]
    )
    conta.valor_final = (
        dinheiro(conta.valor_original)
        + dinheiro(conta.valor_juros)
        + dinheiro(conta.valor_multa)
        - dinheiro(conta.valor_desconto)
    )
    conta.data_ultimo_calculo_encargos = data_calculo
    conta.multa_atraso_aplicada = True


def serializar_calculo_encargos(calculo: dict) -> dict:
    return {
        chave: float(valor) if isinstance(valor, Decimal) else valor
        for chave, valor in calculo.items()
    }
