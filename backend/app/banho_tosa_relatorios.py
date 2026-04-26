"""Agregacoes operacionais do Banho & Tosa."""

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_api.utils import obter_ou_criar_configuracao
from app.banho_tosa_avaliacoes_metrics import calcular_nps_periodo
from app.banho_tosa_custos_helpers import dec, minutos_etapa
from app.banho_tosa_relatorios_helpers import (
    grupo_margem,
    grupo_ocupacao,
    media,
    minutos_agendamento,
    minutos_operacionais,
    montar_alertas,
    percentual,
    periodo,
    proporcao_servico,
    serializar_ocupacao,
    serializar_produtividade,
    total_servicos,
)
from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAtendimento,
    BanhoTosaCustoSnapshot,
    BanhoTosaEtapa,
    BanhoTosaInsumoUsado,
    BanhoTosaRecurso,
)


STATUS_AGENDA_IGNORADOS = {"cancelado", "no_show"}


def gerar_relatorio_operacional(db: Session, tenant_id, data_inicio: date, data_fim: date) -> dict:
    inicio, fim = periodo(data_inicio, data_fim)
    atendimentos = _listar_atendimentos(db, tenant_id, inicio, fim)
    agendamentos = _listar_agendamentos(db, tenant_id, inicio, fim)
    snapshots = _snapshots_por_atendimento(db, tenant_id, atendimentos)
    recursos = _listar_recursos(db, tenant_id)

    margem_servico = _agregar_margem_por_servico(atendimentos, snapshots)
    margem_porte = _agregar_margem_por_porte(atendimentos, snapshots)
    produtividade = _agregar_produtividade(atendimentos)
    desperdicios = _agregar_desperdicios(atendimentos)
    ocupacao = _agregar_ocupacao(db, tenant_id, data_inicio, data_fim, agendamentos, recursos)
    nps = calcular_nps_periodo(db, tenant_id, inicio, fim)

    resumo = _montar_resumo(atendimentos, agendamentos, snapshots, desperdicios, ocupacao, nps)
    return {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "resumo": resumo,
        "margem_por_servico": margem_servico,
        "margem_por_porte": margem_porte,
        "produtividade": produtividade,
        "ocupacao_recursos": ocupacao,
        "desperdicios": desperdicios,
        "alertas": montar_alertas(atendimentos, snapshots, agendamentos),
    }


def _listar_atendimentos(db: Session, tenant_id, inicio: datetime, fim: datetime):
    return (
        db.query(BanhoTosaAtendimento)
        .options(
            joinedload(BanhoTosaAtendimento.pet),
            joinedload(BanhoTosaAtendimento.agendamento).joinedload(BanhoTosaAgendamento.servicos),
            joinedload(BanhoTosaAtendimento.etapas).joinedload(BanhoTosaEtapa.responsavel),
            joinedload(BanhoTosaAtendimento.insumos_usados).joinedload(BanhoTosaInsumoUsado.produto),
        )
        .filter(
            BanhoTosaAtendimento.tenant_id == tenant_id,
            BanhoTosaAtendimento.checkin_em >= inicio,
            BanhoTosaAtendimento.checkin_em <= fim,
        )
        .all()
    )


def _listar_agendamentos(db: Session, tenant_id, inicio: datetime, fim: datetime):
    return (
        db.query(BanhoTosaAgendamento)
        .filter(
            BanhoTosaAgendamento.tenant_id == tenant_id,
            BanhoTosaAgendamento.data_hora_inicio >= inicio,
            BanhoTosaAgendamento.data_hora_inicio <= fim,
            ~BanhoTosaAgendamento.status.in_(STATUS_AGENDA_IGNORADOS),
        )
        .all()
    )


def _snapshots_por_atendimento(db: Session, tenant_id, atendimentos):
    ids = [item.id for item in atendimentos]
    if not ids:
        return {}
    snapshots = db.query(BanhoTosaCustoSnapshot).filter(
        BanhoTosaCustoSnapshot.tenant_id == tenant_id,
        BanhoTosaCustoSnapshot.atendimento_id.in_(ids),
    ).all()
    return {item.atendimento_id: item for item in snapshots}


def _agregar_margem_por_servico(atendimentos, snapshots) -> list[dict]:
    grupos = defaultdict(grupo_margem)
    for atendimento in atendimentos:
        agendamento = atendimento.agendamento
        if not agendamento or not agendamento.servicos:
            _somar_grupo(grupos["sem_servico"], "sem_servico", "Sem servico", snapshots.get(atendimento.id))
            continue
        total = total_servicos(agendamento.servicos)
        for servico in agendamento.servicos:
            chave = str(servico.servico_id or servico.nome_servico_snapshot or "avulso")
            nome = servico.nome_servico_snapshot or "Servico avulso"
            proporcao = proporcao_servico(servico, total, len(agendamento.servicos))
            _somar_grupo(grupos[chave], chave, nome, snapshots.get(atendimento.id), proporcao)
    return _ordenar_margem(grupos)


def _agregar_margem_por_porte(atendimentos, snapshots) -> list[dict]:
    grupos = defaultdict(grupo_margem)
    for atendimento in atendimentos:
        porte = (atendimento.porte_snapshot or getattr(atendimento.pet, "porte", None) or "nao_informado").strip().lower()
        nome = porte.replace("_", " ").title()
        _somar_grupo(grupos[porte], porte, nome, snapshots.get(atendimento.id))
    return _ordenar_margem(grupos)


def _agregar_produtividade(atendimentos) -> list[dict]:
    grupos = {}
    for atendimento in atendimentos:
        for etapa in atendimento.etapas or []:
            if not etapa.responsavel_id:
                continue
            grupo = grupos.setdefault(
                etapa.responsavel_id,
                {"responsavel_id": etapa.responsavel_id, "responsavel_nome": etapa.responsavel.nome if etapa.responsavel else "Sem nome", "etapas": 0, "atendimentos_ids": set(), "minutos_trabalhados": 0},
            )
            grupo["etapas"] += 1
            grupo["atendimentos_ids"].add(atendimento.id)
            grupo["minutos_trabalhados"] += minutos_etapa(etapa)
    return sorted((serializar_produtividade(item) for item in grupos.values()), key=lambda item: item["minutos_trabalhados"], reverse=True)


def _agregar_desperdicios(atendimentos) -> list[dict]:
    grupos = {}
    for atendimento in atendimentos:
        for insumo in atendimento.insumos_usados or []:
            quantidade = dec(insumo.quantidade_desperdicio)
            if quantidade <= 0:
                continue
            grupo = grupos.setdefault(
                insumo.produto_id,
                {"produto_id": insumo.produto_id, "produto_nome": insumo.produto.nome if insumo.produto else "Produto", "unidade": getattr(insumo.produto, "unidade", None), "quantidade_desperdicio": Decimal("0"), "custo_desperdicio": Decimal("0")},
            )
            grupo["quantidade_desperdicio"] += quantidade
            grupo["custo_desperdicio"] += quantidade * dec(insumo.custo_unitario_snapshot)
    return sorted(grupos.values(), key=lambda item: item["custo_desperdicio"], reverse=True)


def _agregar_ocupacao(db: Session, tenant_id, data_inicio: date, data_fim: date, agendamentos, recursos):
    config = obter_ou_criar_configuracao(db, tenant_id)
    minutos_dia = minutos_operacionais(config)
    dias = max((data_fim - data_inicio).days + 1, 1)
    grupos = {recurso.id: grupo_ocupacao(recurso, minutos_dia * dias) for recurso in recursos}
    for agendamento in agendamentos:
        if not agendamento.recurso_id or agendamento.recurso_id not in grupos:
            continue
        grupos[agendamento.recurso_id]["minutos_ocupados"] += minutos_agendamento(agendamento)
    return [serializar_ocupacao(item) for item in grupos.values()]


def _montar_resumo(atendimentos, agendamentos, snapshots, desperdicios, ocupacao, nps: dict) -> dict:
    receita = sum((dec(item.valor_cobrado) for item in snapshots.values()), Decimal("0"))
    custo = sum((dec(item.custo_total) for item in snapshots.values()), Decimal("0"))
    margem = receita - custo
    desperdicio_valor = sum((dec(item["custo_desperdicio"]) for item in desperdicios), Decimal("0"))
    desperdicio_qtd = sum((dec(item["quantidade_desperdicio"]) for item in desperdicios), Decimal("0"))
    ocupacao_media = media([dec(item["ocupacao_percentual"]) for item in ocupacao])
    return {
        "atendimentos": len(atendimentos),
        "agendamentos": len(agendamentos),
        "receita": receita,
        "custo_total": custo,
        "margem_valor": margem,
        "margem_percentual": percentual(margem, receita),
        "ticket_medio": receita / len(atendimentos) if atendimentos else Decimal("0"),
        "desperdicio_valor": desperdicio_valor,
        "desperdicio_quantidade": desperdicio_qtd,
        "ocupacao_media_percentual": ocupacao_media,
        "avaliacoes": nps["avaliacoes"],
        "nps": nps["nps"],
        "promotores": nps["promotores"],
        "neutros": nps["neutros"],
        "detratores": nps["detratores"],
        "nota_servico_media": nps["nota_servico_media"],
    }


def _somar_grupo(grupo, chave: str, nome: str, snapshot, proporcao: Decimal = Decimal("1")):
    grupo["chave"] = chave
    grupo["nome"] = nome
    grupo["atendimentos"] += 1
    if not snapshot:
        return
    grupo["receita"] += dec(snapshot.valor_cobrado) * proporcao
    grupo["custo_total"] += dec(snapshot.custo_total) * proporcao


def _ordenar_margem(grupos) -> list[dict]:
    itens = []
    for grupo in grupos.values():
        margem = grupo["receita"] - grupo["custo_total"]
        itens.append({**grupo, "margem_valor": margem, "margem_percentual": percentual(margem, grupo["receita"])})
    return sorted(itens, key=lambda item: item["receita"], reverse=True)


def _listar_recursos(db: Session, tenant_id):
    return db.query(BanhoTosaRecurso).filter(BanhoTosaRecurso.tenant_id == tenant_id, BanhoTosaRecurso.ativo == True).all()
