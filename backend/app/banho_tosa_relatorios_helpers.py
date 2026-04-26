from datetime import date, datetime, time
from decimal import Decimal

from app.banho_tosa_custos_helpers import dec


def grupo_margem():
    return {"chave": "", "nome": "", "atendimentos": 0, "receita": Decimal("0"), "custo_total": Decimal("0")}


def grupo_ocupacao(recurso, minutos_base: int):
    return {
        "recurso_id": recurso.id,
        "recurso_nome": recurso.nome,
        "recurso_tipo": recurso.tipo,
        "capacidade_simultanea": recurso.capacidade_simultanea,
        "minutos_ocupados": 0,
        "minutos_disponiveis": minutos_base * int(recurso.capacidade_simultanea or 1),
    }


def serializar_ocupacao(item: dict) -> dict:
    return {**item, "ocupacao_percentual": percentual(dec(item["minutos_ocupados"]), dec(item["minutos_disponiveis"]))}


def serializar_produtividade(item: dict) -> dict:
    minutos = int(item["minutos_trabalhados"])
    return {k: v for k, v in item.items() if k != "atendimentos_ids"} | {
        "atendimentos": len(item["atendimentos_ids"]),
        "horas_trabalhadas": Decimal(minutos) / Decimal("60"),
    }


def total_servicos(servicos) -> Decimal:
    return sum((valor_servico(servico) for servico in servicos or []), Decimal("0"))


def valor_servico(servico) -> Decimal:
    return (dec(servico.quantidade) * dec(servico.valor_unitario)) - dec(servico.desconto)


def proporcao_servico(servico, total: Decimal, quantidade_servicos: int) -> Decimal:
    if total > 0:
        return valor_servico(servico) / total
    return Decimal("1") / Decimal(max(quantidade_servicos, 1))


def minutos_agendamento(agendamento) -> int:
    if agendamento.data_hora_inicio and agendamento.data_hora_fim_prevista:
        return max(0, int((agendamento.data_hora_fim_prevista - agendamento.data_hora_inicio).total_seconds() // 60))
    return 60


def minutos_operacionais(config) -> int:
    inicio = parse_hora(config.horario_inicio, time(8, 0))
    fim = parse_hora(config.horario_fim, time(18, 0))
    delta = datetime.combine(date.today(), fim) - datetime.combine(date.today(), inicio)
    return max(0, int(delta.total_seconds() // 60))


def parse_hora(value: str | None, fallback: time) -> time:
    try:
        hora, minuto = str(value or "").split(":")[:2]
        return time(int(hora), int(minuto))
    except (ValueError, TypeError):
        return fallback


def percentual(valor: Decimal, base: Decimal) -> Decimal:
    return (valor / base * Decimal("100")) if base else Decimal("0")


def media(valores: list[Decimal]) -> Decimal:
    return sum(valores, Decimal("0")) / len(valores) if valores else Decimal("0")


def periodo(data_inicio: date, data_fim: date) -> tuple[datetime, datetime]:
    return datetime.combine(data_inicio, time.min), datetime.combine(data_fim, time.max)


def montar_alertas(atendimentos, snapshots, agendamentos) -> list[str]:
    alertas = []
    sem_snapshot = len([item for item in atendimentos if item.id not in snapshots])
    sem_recurso = len([item for item in agendamentos if not item.recurso_id])
    if sem_snapshot:
        alertas.append(f"{sem_snapshot} atendimento(s) sem snapshot de custo recalculado.")
    if sem_recurso:
        alertas.append(f"{sem_recurso} agendamento(s) sem recurso/box definido.")
    return alertas
