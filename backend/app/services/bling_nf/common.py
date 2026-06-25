"""Constantes e normalizadores comuns da integracao Bling NF."""

import re

AUTO_CADASTRO_BING_TAG = "[AUTO-BLING-NF]"


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _regex_token_numerico(valor: str | None) -> str | None:
    texto = _text(valor)
    if not texto:
        return None
    return rf"(?<!\d){re.escape(texto)}(?!\d)"


def _to_float(valor, default: float = 0.0) -> float:
    try:
        return float(valor)
    except Exception:
        return default


def _texto(valor, default: str = "") -> str:
    return str(valor or default).strip()
