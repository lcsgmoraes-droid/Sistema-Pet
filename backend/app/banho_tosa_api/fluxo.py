"""Utilitarios do fluxo operacional do Banho & Tosa."""

from datetime import datetime
from math import ceil
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.banho_tosa_models import (
    BanhoTosaAtendimento,
    BanhoTosaConfiguracao,
    BanhoTosaEtapa,
    BanhoTosaParametroPorte,
)


DEFAULT_FLUXO_ETAPAS = ["chegou", "banho", "secagem", "tosa", "pronto"]
ETAPAS_OPERACIONAIS = {"banho", "secagem", "tosa", "higiene", "preparo"}
ETAPAS_PERMITIDAS = {"chegou", "banho", "secagem", "tosa", "higiene", "preparo", "pronto"}
ETAPA_LABELS = {
    "chegou": "Chegou",
    "banho": "Banho",
    "secagem": "Secagem",
    "tosa": "Tosa",
    "higiene": "Higiene",
    "preparo": "Preparo",
    "pronto": "Pronto",
    "entregue": "Entregue",
}
STATUS_POR_ETAPA = {
    "chegou": "chegou",
    "banho": "em_banho",
    "secagem": "em_secagem",
    "tosa": "em_tosa",
    "higiene": "em_banho",
    "preparo": "em_banho",
    "pronto": "pronto",
}
ETAPA_POR_STATUS = {
    "chegou": "chegou",
    "em_banho": "banho",
    "em_secagem": "secagem",
    "em_tosa": "tosa",
    "pronto": "pronto",
}


def normalizar_fluxo_etapas(valor: Optional[list[str]]) -> list[str]:
    etapas: list[str] = []
    for etapa in valor or DEFAULT_FLUXO_ETAPAS:
        codigo = str(etapa or "").strip().lower()
        if codigo in ETAPAS_PERMITIDAS and codigo not in etapas:
            etapas.append(codigo)

    if "chegou" not in etapas:
        etapas.insert(0, "chegou")
    else:
        etapas = ["chegou"] + [item for item in etapas if item != "chegou"]

    if "pronto" not in etapas:
        etapas.append("pronto")
    else:
        etapas = [item for item in etapas if item != "pronto"] + ["pronto"]

    return etapas or DEFAULT_FLUXO_ETAPAS


def fluxo_da_config(config: Optional[BanhoTosaConfiguracao]) -> list[str]:
    return normalizar_fluxo_etapas(getattr(config, "fluxo_etapas", None))


def etiqueta_etapa(codigo: Optional[str]) -> Optional[str]:
    if not codigo:
        return None
    return ETAPA_LABELS.get(codigo, codigo.replace("_", " ").title())


def status_por_etapa(codigo: str) -> str:
    return STATUS_POR_ETAPA.get(codigo, codigo)


def etapa_ativa(atendimento: BanhoTosaAtendimento) -> Optional[BanhoTosaEtapa]:
    abertas = [
        etapa
        for etapa in getattr(atendimento, "etapas", []) or []
        if etapa.inicio_em and not etapa.fim_em
    ]
    if not abertas:
        return None
    return sorted(abertas, key=lambda etapa: etapa.inicio_em or datetime.min, reverse=True)[0]


def etapa_atual_codigo(atendimento: BanhoTosaAtendimento) -> str:
    aberta = etapa_ativa(atendimento)
    if aberta:
        return aberta.tipo
    return ETAPA_POR_STATUS.get(atendimento.status, atendimento.status)


def proxima_etapa_codigo(atendimento: BanhoTosaAtendimento, fluxo: list[str]) -> Optional[str]:
    atual = etapa_atual_codigo(atendimento)
    if atendimento.status == "pronto":
        return "entregue"
    if atual not in fluxo:
        atual = ETAPA_POR_STATUS.get(atendimento.status, "chegou")
    try:
        indice = fluxo.index(atual)
    except ValueError:
        return None
    if indice + 1 >= len(fluxo):
        return "entregue" if atual == "pronto" else None
    return fluxo[indice + 1]


def fechar_etapa_aberta(
    etapa: BanhoTosaEtapa,
    *,
    fim: Optional[datetime] = None,
    observacoes: Optional[str] = None,
) -> None:
    fim = fim or datetime.now()
    etapa.fim_em = fim
    if etapa.inicio_em:
        segundos = max(0, int((fim - etapa.inicio_em).total_seconds()))
        etapa.duracao_segundos = segundos
        etapa.duracao_minutos = int(ceil(segundos / 60)) if segundos else 0
    if observacoes is not None:
        etapa.observacoes = observacoes


def calcular_tempos_etapa(etapa: BanhoTosaEtapa, agora: Optional[datetime] = None) -> dict:
    previsto_min = int(etapa.tempo_previsto_minutos or 0)
    inicio = etapa.inicio_em
    fim = etapa.fim_em
    if not inicio:
        return {
            "tempo_decorrido_segundos": etapa.duracao_segundos,
            "tempo_restante_segundos": None,
            "atraso_segundos": 0,
            "atrasado": False,
        }

    referencia = fim or agora or datetime.now()
    decorrido = max(0, int((referencia - inicio).total_seconds()))
    restante = (previsto_min * 60) - decorrido if previsto_min else None
    atraso = abs(restante) if restante is not None and restante < 0 else 0
    return {
        "tempo_decorrido_segundos": etapa.duracao_segundos if fim else decorrido,
        "tempo_restante_segundos": restante,
        "atraso_segundos": atraso,
        "atrasado": atraso > 0,
    }


def estado_operacional_atendimento(
    atendimento: BanhoTosaAtendimento,
    config: Optional[BanhoTosaConfiguracao] = None,
) -> dict:
    fluxo = fluxo_da_config(config)
    atual = etapa_atual_codigo(atendimento)
    proxima = proxima_etapa_codigo(atendimento, fluxo)
    aberta = etapa_ativa(atendimento)
    tempos = calcular_tempos_etapa(aberta) if aberta else {}
    return {
        "etapa_atual_codigo": atual,
        "etapa_atual_label": etiqueta_etapa(atual),
        "proxima_etapa_codigo": proxima,
        "proxima_etapa_label": etiqueta_etapa(proxima),
        "tempo_previsto_minutos": getattr(aberta, "tempo_previsto_minutos", None) if aberta else None,
        "tempo_decorrido_segundos": tempos.get("tempo_decorrido_segundos"),
        "tempo_restante_segundos": tempos.get("tempo_restante_segundos"),
        "atraso_segundos": tempos.get("atraso_segundos") or 0,
        "atrasado": bool(tempos.get("atrasado")),
    }


def calcular_tempo_previsto_etapa(
    db: Session,
    tenant_id,
    atendimento: BanhoTosaAtendimento,
    tipo: str,
) -> int:
    tipo = str(tipo or "").strip().lower()
    if tipo not in ETAPAS_OPERACIONAIS:
        return 0

    parametro = _parametro_porte_atendimento(db, tenant_id, atendimento)
    if parametro:
        tempo = {
            "banho": parametro.tempo_banho_min,
            "secagem": parametro.tempo_secagem_min,
            "tosa": parametro.tempo_tosa_min,
            "higiene": min(parametro.tempo_tosa_min or 15, 30),
            "preparo": 10,
        }.get(tipo, 0)
        if _pelagem_longa(atendimento) and tipo in {"banho", "secagem", "tosa"}:
            tempo += int(getattr(parametro, "tempo_extra_pelo_longo_min", 0) or 0)
        if tempo:
            return int(tempo)

    return {
        "banho": 30,
        "secagem": 30,
        "tosa": 45,
        "higiene": 15,
        "preparo": 10,
    }.get(tipo, 0)


def ordem_fluxo_para(tipo: str, fluxo: list[str]) -> Optional[int]:
    try:
        return fluxo.index(tipo)
    except ValueError:
        return None


def _parametro_porte_atendimento(db: Session, tenant_id, atendimento: BanhoTosaAtendimento):
    porte = (atendimento.porte_snapshot or getattr(atendimento.pet, "porte", None) or "").strip().lower()
    if not porte:
        return None
    return db.query(BanhoTosaParametroPorte).filter(
        BanhoTosaParametroPorte.tenant_id == tenant_id,
        func.lower(BanhoTosaParametroPorte.porte) == porte,
    ).first()


def _pelagem_longa(atendimento: BanhoTosaAtendimento) -> bool:
    pelagem = (atendimento.pelagem_snapshot or "").strip().lower()
    return "long" in pelagem or "longo" in pelagem or "comprid" in pelagem
