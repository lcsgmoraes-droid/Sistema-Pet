"""Helpers for customer alerts shown in the POS."""

from __future__ import annotations

import json
from typing import Any


VALID_PRIORITIES = {"aviso", "importante", "info"}


def _clean_text(value: Any, max_length: int) -> str:
    text = str(value or "").strip()
    if len(text) > max_length:
        return text[:max_length].strip()
    return text


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "nao", "não", "no"}
    return value is not False


def _coerce_items(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (TypeError, ValueError):
            return []
        return decoded if isinstance(decoded, list) else []
    return value if isinstance(value, list) else []


def normalizar_alertas_pdv(value: Any) -> list[dict[str, Any]]:
    """Normalize customer POS alerts to a stable JSON payload."""
    alertas: list[dict[str, Any]] = []

    for item in _coerce_items(value):
        if not isinstance(item, dict):
            continue

        titulo = _clean_text(
            item.get("titulo") or item.get("tag") or item.get("label"),
            80,
        )
        mensagem = _clean_text(
            item.get("mensagem") or item.get("observacao") or item.get("descricao"),
            500,
        )

        if not titulo and not mensagem:
            continue
        if not titulo:
            titulo = "Observacao"

        prioridade = _clean_text(item.get("prioridade") or "aviso", 20).lower()
        if prioridade not in VALID_PRIORITIES:
            prioridade = "aviso"

        alertas.append(
            {
                "titulo": titulo,
                "mensagem": mensagem,
                "prioridade": prioridade,
                "ativo": _coerce_bool(item.get("ativo", True)),
            }
        )

    return alertas


def alertas_pdv_ativos(value: Any) -> list[dict[str, Any]]:
    return [alerta for alerta in normalizar_alertas_pdv(value) if alerta["ativo"]]
