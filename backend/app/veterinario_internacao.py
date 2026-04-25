"""Helpers operacionais de internacao veterinaria."""

import json
import re
from datetime import datetime
from typing import Optional

from fastapi import HTTPException

from .veterinario_core import _serializar_datetime_vet
from .veterinario_models import EvolucaoInternacao, InternacaoProcedimentoAgenda, InternacaoVet


_BAIA_MOTIVO_RE = re.compile(r"\s*\[BAIA:(?P<baia>[^\]]+)\]\s*$")
_PROC_PREFIX = "[PROC_INT]"


def _resolver_data_entrada_exibicao_internacao(
    internacao: InternacaoVet,
    registros: Optional[list[EvolucaoInternacao]] = None,
) -> Optional[datetime]:
    data_entrada = _serializar_datetime_vet(internacao.data_entrada)
    if not registros:
        return data_entrada

    candidatos = []
    for registro in registros:
        data_registro = _serializar_datetime_vet(registro.data_hora)
        if data_registro:
            candidatos.append(data_registro)

    if not candidatos:
        return data_entrada

    primeira_movimentacao = min(candidatos)
    if not data_entrada:
        return primeira_movimentacao

    try:
        diff_horas = abs((primeira_movimentacao - data_entrada).total_seconds()) / 3600
        if data_entrada.date() == primeira_movimentacao.date() and 2.5 <= diff_horas <= 3.5:
            return primeira_movimentacao
    except Exception:
        return data_entrada

    return data_entrada


def _pack_motivo_baia(motivo: str, baia: Optional[str]) -> str:
    motivo_limpo = (motivo or "").strip()
    baia_limpa = (baia or "").strip()
    if not baia_limpa:
        return motivo_limpo
    return f"{motivo_limpo} [BAIA:{baia_limpa}]"


def _split_motivo_baia(motivo: Optional[str]) -> tuple[str, Optional[str]]:
    texto = (motivo or "").strip()
    match = _BAIA_MOTIVO_RE.search(texto)
    if not match:
        return texto, None
    baia = (match.group("baia") or "").strip() or None
    motivo_sem_baia = _BAIA_MOTIVO_RE.sub("", texto).strip()
    return motivo_sem_baia, baia


def _normalizar_baia(baia: Optional[str]) -> Optional[str]:
    valor = (baia or "").strip()
    if not valor:
        return None
    return valor.lower()


def _build_procedimento_observacao(payload: dict) -> str:
    return f"{_PROC_PREFIX}{json.dumps(payload, ensure_ascii=False)}"


def _parse_procedimento_observacao(observacoes: Optional[str]) -> Optional[dict]:
    texto = (observacoes or "").strip()
    if not texto.startswith(_PROC_PREFIX):
        return None
    bruto = texto[len(_PROC_PREFIX):]
    if not bruto:
        return None
    try:
        parsed = json.loads(bruto)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _separar_evolucoes_e_procedimentos(registros: list[EvolucaoInternacao]) -> tuple[list[dict], list[dict]]:
    evolucoes_formatadas = []
    procedimentos_formatados = []

    for ev in registros:
        proc_payload = _parse_procedimento_observacao(ev.observacoes)
        if proc_payload:
            procedimentos_formatados.append({
                "id": ev.id,
                "data_hora": _serializar_datetime_vet(ev.data_hora),
                "status": proc_payload.get("status") or "concluido",
                "tipo_registro": proc_payload.get("tipo_registro") or "procedimento",
                "horario_agendado": proc_payload.get("horario_agendado"),
                "medicamento": proc_payload.get("medicamento"),
                "dose": proc_payload.get("dose"),
                "via": proc_payload.get("via"),
                "quantidade_prevista": proc_payload.get("quantidade_prevista"),
                "quantidade_executada": proc_payload.get("quantidade_executada"),
                "quantidade_desperdicio": proc_payload.get("quantidade_desperdicio"),
                "unidade_quantidade": proc_payload.get("unidade_quantidade"),
                "insumos": proc_payload.get("insumos") or [],
                "estoque_baixado": bool(proc_payload.get("estoque_baixado")),
                "estoque_movimentacao_ids": proc_payload.get("estoque_movimentacao_ids") or [],
                "executado_por": proc_payload.get("executado_por"),
                "horario_execucao": proc_payload.get("horario_execucao"),
                "observacao_execucao": proc_payload.get("observacao_execucao"),
                "observacoes_agenda": proc_payload.get("observacoes_agenda"),
            })
            continue

        evolucoes_formatadas.append({
            "id": ev.id,
            "data_hora": _serializar_datetime_vet(ev.data_hora),
            "temperatura": ev.temperatura,
            "freq_cardiaca": ev.frequencia_cardiaca,
            "freq_respiratoria": ev.frequencia_respiratoria,
            "nivel_dor": ev.nivel_dor,
            "pressao_sistolica": ev.pressao_sistolica,
            "glicemia": ev.glicemia,
            "peso": ev.peso,
            "observacoes": ev.observacoes,
        })

    return evolucoes_formatadas, procedimentos_formatados


def _resolver_user_id_vet(user, detail: str) -> int:
    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail=detail)
    return user_id


def _resolver_tenant_id_vet(user, tenant_id, detail: str):
    if tenant_id is None:
        tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None and isinstance(user, dict):
        tenant_id = user.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail=detail)
    return tenant_id


def _datetime_iso_vet(value: Optional[datetime]) -> Optional[str]:
    serializado = _serializar_datetime_vet(value)
    return serializado.isoformat() if serializado else None


def _serializar_procedimento_agenda_internacao(item: InternacaoProcedimentoAgenda) -> dict:
    _, box = _split_motivo_baia(item.internacao.motivo if item.internacao else None)
    pet_nome = item.pet.nome if item.pet else None
    return {
        "id": item.id,
        "backend_id": item.id,
        "internacao_id": item.internacao_id,
        "pet_id": item.pet_id,
        "pet_nome": pet_nome or f"Pet #{item.pet_id}",
        "baia": box or "Sem baia",
        "horario": _serializar_datetime_vet(item.horario_agendado),
        "horario_agendado": _serializar_datetime_vet(item.horario_agendado),
        "medicamento": item.medicamento,
        "dose": item.dose,
        "quantidade_prevista": item.quantidade_prevista,
        "quantidade_executada": item.quantidade_executada,
        "quantidade_desperdicio": item.quantidade_desperdicio,
        "unidade_quantidade": item.unidade_quantidade,
        "via": item.via,
        "lembrete_min": item.lembrete_minutos,
        "observacoes": item.observacoes_agenda,
        "observacoes_agenda": item.observacoes_agenda,
        "status": item.status,
        "feito": item.status == "concluido",
        "feito_por": item.executado_por or "",
        "executado_por": item.executado_por,
        "horario_execucao": _serializar_datetime_vet(item.horario_execucao),
        "observacao_execucao": item.observacao_execucao or "",
        "procedimento_evolucao_id": item.procedimento_evolucao_id,
    }


def _build_payload_procedimento_agenda_internacao(item: InternacaoProcedimentoAgenda) -> dict:
    return {
        "status": item.status,
        "tipo_registro": "procedimento_agendado",
        "horario_agendado": _datetime_iso_vet(item.horario_agendado),
        "medicamento": item.medicamento,
        "dose": item.dose,
        "via": item.via,
        "quantidade_prevista": item.quantidade_prevista,
        "quantidade_executada": item.quantidade_executada,
        "quantidade_desperdicio": item.quantidade_desperdicio or 0,
        "unidade_quantidade": item.unidade_quantidade,
        "insumos": [],
        "estoque_baixado": False,
        "estoque_movimentacao_ids": [],
        "observacoes_agenda": item.observacoes_agenda,
        "executado_por": item.executado_por,
        "horario_execucao": _datetime_iso_vet(item.horario_execucao),
        "observacao_execucao": item.observacao_execucao,
    }
