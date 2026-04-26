from decimal import Decimal

from app.banho_tosa_custos import EquipamentoUso, InsumoCusto, calcular_custo_agua
from app.banho_tosa_custos_helpers import dec, minutos_etapa


ETAPAS_COM_AGUA = {"banho", "higiene", "preparo"}


def valor_cobrado_atendimento(atendimento) -> Decimal:
    agendamento = atendimento.agendamento
    if not agendamento:
        return Decimal("0")

    total = Decimal("0")
    for item in agendamento.servicos or []:
        total += (dec(item.quantidade) * dec(item.valor_unitario)) - dec(item.desconto)
    if total > 0:
        return total
    return dec(agendamento.valor_previsto)


def mapear_insumos_custo(insumos):
    return [
        InsumoCusto(
            quantidade_usada=item.quantidade_usada,
            quantidade_desperdicio=item.quantidade_desperdicio,
            custo_unitario_snapshot=item.custo_unitario_snapshot,
        )
        for item in insumos or []
    ]


def calcular_agua_atendimento(atendimento, config, parametro) -> Decimal:
    minutos_banho = sum(minutos_etapa(etapa) for etapa in atendimento.etapas or [] if etapa.tipo in ETAPAS_COM_AGUA)
    if minutos_banho > 0:
        return calcular_custo_agua(
            custo_litro_agua=config.custo_litro_agua,
            vazao_chuveiro_litros_min=config.vazao_chuveiro_litros_min,
            minutos_banho=minutos_banho,
        )
    return calcular_custo_agua(
        custo_litro_agua=config.custo_litro_agua,
        agua_padrao_litros=getattr(parametro, "agua_padrao_litros", 0),
    )


def mapear_equipamentos_custo(atendimento, config, parametro):
    usos = []
    for etapa in atendimento.etapas or []:
        minutos = minutos_etapa(etapa)
        recurso = etapa.recurso
        if minutos <= 0 or not recurso:
            continue
        usos.append(
            EquipamentoUso(
                potencia_watts=recurso.potencia_watts or 0,
                minutos_uso=minutos,
                custo_kwh=config.custo_kwh,
                custo_manutencao_hora=recurso.custo_manutencao_hora,
            )
        )
    if not usos and parametro and dec(parametro.energia_padrao_kwh) > 0:
        usos.append(EquipamentoUso(kwh_real=parametro.energia_padrao_kwh, custo_kwh=config.custo_kwh))
    return usos
