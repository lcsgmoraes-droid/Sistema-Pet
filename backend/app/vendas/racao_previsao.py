"""Validacao e calculo da previsao manual de termino de racao no PDV."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException


@dataclass(frozen=True)
class PrevisaoFimRacao:
    data_prevista: date | None
    prazo_dias: int | None


@dataclass(frozen=True)
class PrevisaoFimRacaoResolvida:
    data_prevista: datetime
    intervalo_dias: int
    origem: str


def _valor(item: Any, campo: str) -> Any:
    if isinstance(item, dict):
        return item.get(campo)
    return getattr(item, campo, None)


def validar_previsao_fim_racao(
    item: Any,
    *,
    produto: Any,
    cliente_id: int | None,
) -> PrevisaoFimRacao:
    """Impede previsao sem cliente, fora de racao ou com duas escolhas."""
    data_prevista = _valor(item, "racao_data_prevista_fim")
    prazo_dias = _valor(item, "racao_prazo_estimado_dias")
    if data_prevista is None and prazo_dias is None:
        return PrevisaoFimRacao(None, None)

    if data_prevista is not None and prazo_dias is not None:
        raise HTTPException(
            status_code=400,
            detail="Informe a data ou o prazo para a ração acabar, não os dois.",
        )
    if not cliente_id:
        raise HTTPException(
            status_code=400,
            detail="Selecione o cliente para criar o aviso de término da ração.",
        )
    if not produto or not bool(getattr(produto, "eh_racao", False)):
        raise HTTPException(
            status_code=400,
            detail="A previsão de término só pode ser informada para produtos de ração.",
        )

    return PrevisaoFimRacao(data_prevista, prazo_dias)


def resolver_previsao_fim_racao(
    item: Any,
    *,
    data_compra: datetime,
) -> PrevisaoFimRacaoResolvida | None:
    """Converte a data ou o prazo persistido na data real do lembrete."""
    data_informada = _valor(item, "racao_data_prevista_fim")
    prazo_informado = _valor(item, "racao_prazo_estimado_dias")

    if data_informada is not None:
        intervalo = (data_informada - data_compra.date()).days
        if intervalo < 1:
            return None
        return PrevisaoFimRacaoResolvida(
            data_prevista=datetime.combine(data_informada, data_compra.time()),
            intervalo_dias=intervalo,
            origem="informado_venda_data",
        )

    if prazo_informado is None:
        return None

    prazo = int(prazo_informado)
    if prazo < 1 or prazo > 365:
        return None
    return PrevisaoFimRacaoResolvida(
        data_prevista=data_compra + timedelta(days=prazo),
        intervalo_dias=prazo,
        origem="informado_venda_prazo",
    )


__all__ = [
    "PrevisaoFimRacao",
    "PrevisaoFimRacaoResolvida",
    "resolver_previsao_fim_racao",
    "validar_previsao_fim_racao",
]
