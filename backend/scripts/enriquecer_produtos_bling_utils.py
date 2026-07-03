"""Normalizacao e leitura de campos do enriquecimento Bling."""

from __future__ import annotations

import re
from typing import Dict, Iterable, Optional


def normalize_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def normalize_key(value: Optional[str]) -> str:
    text = normalize_text(value).upper()
    return re.sub(r"[^A-Z0-9]", "", text)


def parse_decimal(value: Optional[str]) -> Optional[float]:
    text = normalize_text(value)
    if not text:
        return None
    text = text.replace("R$", "").replace(" ", "")
    # Heuristica segura para pt-BR / en-US
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def only_digits(value: Optional[str]) -> str:
    return re.sub(r"\D", "", normalize_text(value))


def build_family_key(value: Optional[str]) -> str:
    text = normalize_text(value).upper()
    if not text:
        return ""
    text = re.sub(r"\bQUANTIDADE\s*:\s*\d+\s*UNIDADES?\b", "", text)
    text = re.sub(r"\bPAI\b", "", text)
    return normalize_text(text)


def map_origem(value: Optional[str]) -> Optional[str]:
    text = normalize_text(value)
    if not text:
        return None
    if (
        text.isdigit()
        and len(text) == 1
        and text in {"0", "1", "2", "3", "4", "5", "6", "7", "8"}
    ):
        return text
    upper = text.upper()
    if "NACIONAL" in upper:
        return "0"
    if "ESTRANGEIRA" in upper:
        return "1"
    return None


def pick(row: Dict[str, str], keys: Iterable[str]) -> str:
    for key in keys:
        if key in row and normalize_text(row.get(key)):
            return normalize_text(row.get(key))
    return ""
