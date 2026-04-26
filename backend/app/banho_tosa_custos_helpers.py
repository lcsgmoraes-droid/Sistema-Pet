"""Helpers pequenos para snapshots de custo do Banho & Tosa."""

from decimal import Decimal

from app.banho_tosa_models import BanhoTosaCustoSnapshot


def dec(value, default="0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def minutos_etapa(etapa) -> int:
    if etapa.duracao_minutos is not None:
        return max(0, int(etapa.duracao_minutos or 0))
    if etapa.inicio_em and etapa.fim_em:
        return max(0, int((etapa.fim_em - etapa.inicio_em).total_seconds() // 60))
    return 0


def montar_detalhes_snapshot(atendimento, parametro, mao_obra_detalhes, taxi_detalhes) -> dict:
    return {
        "origem": "operacional",
        "atendimento_status": atendimento.status,
        "porte_usado": getattr(parametro, "porte", None) or atendimento.porte_snapshot,
        "etapas": [
            {"tipo": etapa.tipo, "minutos": minutos_etapa(etapa), "recurso_id": etapa.recurso_id}
            for etapa in atendimento.etapas or []
        ],
        "mao_obra": mao_obra_detalhes,
        "taxi_dog": taxi_detalhes,
    }


def serializar_snapshot_custo(registro: BanhoTosaCustoSnapshot) -> dict:
    return {
        "id": registro.id,
        "atendimento_id": registro.atendimento_id,
        "valor_cobrado": registro.valor_cobrado,
        "custo_insumos": registro.custo_insumos,
        "custo_agua": registro.custo_agua,
        "custo_energia": registro.custo_energia,
        "custo_mao_obra": registro.custo_mao_obra,
        "custo_comissao": registro.custo_comissao,
        "custo_taxi_dog": registro.custo_taxi_dog,
        "custo_taxas_pagamento": registro.custo_taxas_pagamento,
        "custo_rateio_operacional": registro.custo_rateio_operacional,
        "custo_total": registro.custo_total,
        "margem_valor": registro.margem_valor,
        "margem_percentual": registro.margem_percentual,
        "detalhes_json": registro.detalhes_json,
    }
