"""Agrupamento de movimentacoes do fluxo de caixa."""

from datetime import date, timedelta
from typing import List

from app.financeiro.fluxo_caixa_schemas import (
    FluxoCaixaMovimentacao,
    FluxoCaixaPeriodo,
)


def _agrupar_por_periodo(
    movimentacoes: List[FluxoCaixaMovimentacao],
    dt_inicio: date,
    dt_fim: date,
    agrupamento: str,
    saldo_inicial: float,
) -> List[FluxoCaixaPeriodo]:
    """Agrupar movimentações por período (dia/semana/mês)"""

    periodos_dict = {}

    if agrupamento == "dia":
        # Criar entrada para cada dia
        dia_atual = dt_inicio
        while dia_atual <= dt_fim:
            chave = dia_atual.isoformat()
            periodos_dict[chave] = {
                "data": dia_atual.strftime("%d/%m/%Y"),
                "data_inicio": dia_atual,
                "data_fim": dia_atual,
                "previsto_entradas": 0,
                "previsto_saidas": 0,
                "realizado_entradas": 0,
                "realizado_saidas": 0,
            }
            dia_atual += timedelta(days=1)

        # Acumular movimentações
        for mov in movimentacoes:
            chave = mov.data.isoformat()
            if chave in periodos_dict:
                if mov.status == "previsto":
                    if mov.tipo == "entrada":
                        periodos_dict[chave]["previsto_entradas"] += mov.valor
                    else:
                        periodos_dict[chave]["previsto_saidas"] += mov.valor
                else:  # realizado
                    if mov.tipo == "entrada":
                        periodos_dict[chave]["realizado_entradas"] += mov.valor
                    else:
                        periodos_dict[chave]["realizado_saidas"] += mov.valor

    elif agrupamento == "semana":
        # Agrupar por semanas
        import calendar

        semana_num = 1
        dia_atual = dt_inicio

        while dia_atual <= dt_fim:
            # Encontrar início e fim da semana (segunda a domingo)
            inicio_semana = dia_atual - timedelta(days=dia_atual.weekday())
            fim_semana = inicio_semana + timedelta(days=6)

            # Ajustar limites
            if inicio_semana < dt_inicio:
                inicio_semana = dt_inicio
            if fim_semana > dt_fim:
                fim_semana = dt_fim

            chave = f"semana_{semana_num}"
            if chave not in periodos_dict:
                periodos_dict[chave] = {
                    "data": f"Semana {semana_num} ({inicio_semana.strftime('%d/%m')} - {fim_semana.strftime('%d/%m')})",
                    "data_inicio": inicio_semana,
                    "data_fim": fim_semana,
                    "previsto_entradas": 0,
                    "previsto_saidas": 0,
                    "realizado_entradas": 0,
                    "realizado_saidas": 0,
                }

            dia_atual = fim_semana + timedelta(days=1)
            semana_num += 1

        # Acumular movimentações
        for mov in movimentacoes:
            for chave, periodo in periodos_dict.items():
                if periodo["data_inicio"] <= mov.data <= periodo["data_fim"]:
                    if mov.status == "previsto":
                        if mov.tipo == "entrada":
                            periodo["previsto_entradas"] += mov.valor
                        else:
                            periodo["previsto_saidas"] += mov.valor
                    else:
                        if mov.tipo == "entrada":
                            periodo["realizado_entradas"] += mov.valor
                        else:
                            periodo["realizado_saidas"] += mov.valor
                    break

    elif agrupamento == "mes":
        # Agrupar por meses
        meses_unicos = set()
        dia_atual = dt_inicio
        while dia_atual <= dt_fim:
            meses_unicos.add((dia_atual.year, dia_atual.month))
            # Avançar para o próximo mês
            if dia_atual.month == 12:
                dia_atual = date(dia_atual.year + 1, 1, 1)
            else:
                dia_atual = date(dia_atual.year, dia_atual.month + 1, 1)

        import calendar

        meses_pt = [
            "Janeiro",
            "Fevereiro",
            "Março",
            "Abril",
            "Maio",
            "Junho",
            "Julho",
            "Agosto",
            "Setembro",
            "Outubro",
            "Novembro",
            "Dezembro",
        ]

        for ano, mes in sorted(meses_unicos):
            inicio_mes = date(ano, mes, 1)
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            fim_mes = date(ano, mes, ultimo_dia)

            # Ajustar limites
            if inicio_mes < dt_inicio:
                inicio_mes = dt_inicio
            if fim_mes > dt_fim:
                fim_mes = dt_fim

            chave = f"{ano}-{mes:02d}"
            periodos_dict[chave] = {
                "data": f"{meses_pt[mes - 1]}/{ano}",
                "data_inicio": inicio_mes,
                "data_fim": fim_mes,
                "previsto_entradas": 0,
                "previsto_saidas": 0,
                "realizado_entradas": 0,
                "realizado_saidas": 0,
            }

        # Acumular movimentações
        for mov in movimentacoes:
            chave = f"{mov.data.year}-{mov.data.month:02d}"
            if chave in periodos_dict:
                if mov.status == "previsto":
                    if mov.tipo == "entrada":
                        periodos_dict[chave]["previsto_entradas"] += mov.valor
                    else:
                        periodos_dict[chave]["previsto_saidas"] += mov.valor
                else:
                    if mov.tipo == "entrada":
                        periodos_dict[chave]["realizado_entradas"] += mov.valor
                    else:
                        periodos_dict[chave]["realizado_saidas"] += mov.valor

    # Calcular saldos acumulados
    periodos = []
    saldo_acumulado = saldo_inicial
    saldo_previsto_acumulado = saldo_inicial

    for chave in sorted(periodos_dict.keys()):
        p = periodos_dict[chave]

        # Saldo realizado
        saldo_acumulado += p["realizado_entradas"] - p["realizado_saidas"]

        # Saldo previsto (realizado + previsto)
        saldo_previsto_acumulado = (
            saldo_acumulado + p["previsto_entradas"] - p["previsto_saidas"]
        )

        periodos.append(
            FluxoCaixaPeriodo(
                data=p["data"],
                data_inicio=p["data_inicio"],
                data_fim=p["data_fim"],
                previsto_entradas=p["previsto_entradas"],
                previsto_saidas=p["previsto_saidas"],
                previsto_saldo=saldo_previsto_acumulado,
                realizado_entradas=p["realizado_entradas"],
                realizado_saidas=p["realizado_saidas"],
                realizado_saldo=saldo_acumulado,
                saldo_inicial=saldo_inicial
                if len(periodos) == 0
                else periodos[-1].saldo_final,
                saldo_final=saldo_acumulado,
            )
        )

        # Atualizar saldo inicial do próximo período
        if periodos:
            saldo_inicial = saldo_acumulado

    return periodos
