from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from app.utils.correlation import current_correlation_id


def _utcnow() -> datetime:
    return datetime.utcnow()


def normalizar_data_evento_monitor(value: Any) -> datetime | None:
    if value is None:
        return None

    dt: datetime | None = None
    if isinstance(value, datetime):
        dt = value
    else:
        texto = _text(value)
        if not texto:
            return None
        texto = texto.replace("Z", "+00:00")
        if "T" not in texto and " " in texto:
            texto = texto.replace(" ", "T", 1)
        try:
            dt = datetime.fromisoformat(texto)
        except ValueError:
            return None

    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def serializar_data_evento_monitor(value: datetime | None) -> str | None:
    dt = normalizar_data_evento_monitor(value)
    if not dt:
        return None
    return dt.replace(tzinfo=timezone.utc).isoformat()


def _text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _primeiro_preenchido(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "hex") and callable(getattr(value, "hex", None)):
        try:
            return str(value)
        except Exception:
            return None
    return value


def _payload_with_correlation(payload: dict | None) -> dict:
    safe_payload = _json_safe(payload or {})
    if not isinstance(safe_payload, dict):
        safe_payload = {"value": safe_payload}

    correlation_id = current_correlation_id("bling.flow.event")
    safe_payload.setdefault("request_id", correlation_id)
    safe_payload.setdefault("correlation_id", correlation_id)
    return safe_payload


def _nf_bling_id_valido(value: Any) -> str | None:
    texto = _text(value)
    if not texto or texto in {"0", "-1"}:
        return None
    return texto


def _normalizar_contexto_nf(nf: dict | None) -> dict:
    nf = dict(_dict(nf))
    if not nf:
        return {}

    nf_id = _nf_bling_id_valido(_primeiro_preenchido(nf.get("id"), nf.get("nfe_id")))
    if nf_id:
        if "id" in nf or "nfe_id" not in nf:
            nf["id"] = nf_id
        else:
            nf["nfe_id"] = nf_id
    else:
        nf.pop("id", None)
        nf.pop("nfe_id", None)

    possui_referencia_util = bool(
        nf_id
        or _text(nf.get("numero"))
        or _text(_primeiro_preenchido(nf.get("chaveAcesso"), nf.get("chave")))
        or _text(_primeiro_preenchido(nf.get("situacao"), nf.get("status")))
        or _text(_primeiro_preenchido(nf.get("data_emissao"), nf.get("dataEmissao")))
        or nf.get("valor_total") not in (None, "")
    )
    return nf if possui_referencia_util else {}


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
