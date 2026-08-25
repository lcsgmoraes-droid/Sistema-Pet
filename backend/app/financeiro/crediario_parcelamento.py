"""Regras compartilhadas para o parcelamento do crediario."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


INTERVALOS_CREDIARIO = frozenset({"7_dias", "15_dias", "mensal"})


def normalizar_intervalo_crediario(
    intervalo: str | None, *, numero_parcelas: int
) -> str | None:
    """Normaliza o intervalo, mantendo 1x sem uma escolha desnecessaria."""
    if numero_parcelas <= 1:
        return None

    intervalo_normalizado = str(intervalo or "mensal").strip().lower()
    if intervalo_normalizado not in INTERVALOS_CREDIARIO:
        raise ValueError(
            "Intervalo do crediario invalido. Use 7 dias, 15 dias ou mensal."
        )
    return intervalo_normalizado


def distribuir_valor_parcelas(
    valor_total: Decimal | float | str, numero_parcelas: int
) -> list[Decimal]:
    """Divide o total e deixa a ultima parcela absorver os centavos restantes."""
    if numero_parcelas < 1:
        raise ValueError("numero_parcelas deve ser maior que zero")

    centavo = Decimal("0.01")
    total = Decimal(str(valor_total)).quantize(centavo, rounding=ROUND_HALF_UP)
    valor_base = (total / numero_parcelas).quantize(centavo, rounding=ROUND_HALF_UP)
    parcelas = [valor_base for _ in range(max(numero_parcelas - 1, 0))]
    parcelas.append(
        (total - sum(parcelas, Decimal("0.00"))).quantize(
            centavo, rounding=ROUND_HALF_UP
        )
    )
    return parcelas


def _adicionar_meses_preservando_dia(
    primeira_data: date, meses: int, *, dia_referencia: int
) -> date:
    indice_mes = primeira_data.year * 12 + (primeira_data.month - 1) + meses
    ano, mes_zero = divmod(indice_mes, 12)
    mes = mes_zero + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(dia_referencia, ultimo_dia))


def gerar_vencimentos_crediario(
    primeira_data: date,
    numero_parcelas: int,
    intervalo: str | None,
) -> list[date]:
    """Gera vencimentos fixos ou mensais preservando o dia originalmente escolhido."""
    if numero_parcelas < 1:
        raise ValueError("numero_parcelas deve ser maior que zero")

    intervalo_normalizado = normalizar_intervalo_crediario(
        intervalo, numero_parcelas=numero_parcelas
    )
    if numero_parcelas == 1:
        return [primeira_data]
    if intervalo_normalizado == "7_dias":
        return [
            primeira_data + timedelta(days=7 * indice)
            for indice in range(numero_parcelas)
        ]
    if intervalo_normalizado == "15_dias":
        return [
            primeira_data + timedelta(days=15 * indice)
            for indice in range(numero_parcelas)
        ]

    return [
        _adicionar_meses_preservando_dia(
            primeira_data, indice, dia_referencia=primeira_data.day
        )
        for indice in range(numero_parcelas)
    ]


def montar_plano_crediario(
    *,
    valor_total: Decimal | float | str,
    numero_parcelas: int,
    primeira_data: date,
    intervalo: str | None,
) -> list[dict[str, object]]:
    """Monta a previa autoritativa usada para gravar as contas a receber."""
    valores = distribuir_valor_parcelas(valor_total, numero_parcelas)
    vencimentos = gerar_vencimentos_crediario(primeira_data, numero_parcelas, intervalo)
    return [
        {
            "numero": indice,
            "total_parcelas": numero_parcelas,
            "valor": valor,
            "data_vencimento": vencimento,
        }
        for indice, (valor, vencimento) in enumerate(
            zip(valores, vencimentos, strict=True), start=1
        )
    ]
