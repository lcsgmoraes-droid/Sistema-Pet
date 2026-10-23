"""Estado do pedido de cancelamento, separado da situação fiscal da nota."""

import re
from datetime import datetime, timedelta, timezone

from app.utils.serialization import safe_datetime_to_iso
from app.vendas.fiscal_status import pendencia_fiscal_cancelamento

STATUS_CANCELAMENTO = {"pendente", "solicitado", "recusado", "confirmado"}


def motivo_seguro(value):
    from app.intnfe.client import _safe_validation_errors

    if not isinstance(value, str) or not value.strip():
        return None
    mensagens = _safe_validation_errors({"erros": [value]})
    return mensagens[0] if mensagens else None


def data_evento(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return (
        parsed.replace(tzinfo=timezone.utc)
        if parsed.tzinfo is None
        else parsed.astimezone(timezone.utc)
    )


def resultado_cancelamento(payload, *, somente_evento=False):
    if not isinstance(payload, dict):
        return None
    tipo = str(payload.get("tipoEventoCodigo") or "")
    if somente_evento and tipo not in {"110111", "110112"}:
        return None
    codigo = str(payload.get("codigoRetorno") or payload.get("erro") or "").strip()
    codigo = codigo if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", codigo) else None
    motivo = motivo_seguro(payload.get("motivoRetorno") or payload.get("mensagem"))
    if payload.get("autorizado") is True and payload.get("protocolo"):
        status = "confirmado"
    elif (
        payload.get("autorizado") is False
        or payload.get("success") is False
        or payload.get("erro")
        or (codigo and codigo.isdigit() and int(codigo) >= 200)
    ):
        status = "recusado"
        motivo = motivo or "Solicitação de cancelamento recusada pelo emissor."
    else:
        return None
    return {
        "status": status,
        "codigo": codigo,
        "motivo": motivo,
        "criado_em": data_evento(payload.get("criadoEm")),
    }


def ultimo_cancelamento(eventos, *, solicitado_em=None):
    resultados = [
        resultado
        for evento in eventos
        if (resultado := resultado_cancelamento(evento, somente_evento=True))
    ]
    confirmados = [r for r in resultados if r["status"] == "confirmado"]
    if confirmados:
        resultados = confirmados
    elif (inicio := data_evento(solicitado_em)) is not None:
        resultados = [
            r
            for r in resultados
            if r["criado_em"] is not None
            and r["criado_em"] >= inicio - timedelta(seconds=5)
        ]
    return max(
        resultados,
        key=lambda r: r["criado_em"] or datetime.min.replace(tzinfo=timezone.utc),
        default=None,
    )


def aplicar_resultado_cancelamento(venda, resultado):
    if not resultado:
        return
    venda.nfe_cancelamento_status = resultado["status"]
    venda.nfe_cancelamento_codigo = resultado.get("codigo")
    venda.nfe_cancelamento_motivo = resultado.get("motivo")
    if not getattr(venda, "nfe_cancelamento_solicitado_em", None) and resultado.get(
        "criado_em"
    ):
        venda.nfe_cancelamento_solicitado_em = resultado["criado_em"]


def campos_cancelamento(venda):
    pendencia = pendencia_fiscal_cancelamento(venda)
    status = getattr(venda, "nfe_cancelamento_status", None)
    status = (
        status if isinstance(status, str) and status in STATUS_CANCELAMENTO else None
    )
    if str(getattr(venda, "nfe_status", "") or "").lower() in {
        "cancelada",
        "cancelado",
    }:
        status = "confirmado"
    elif status is None and pendencia:
        status = "pendente"
    codigo = getattr(venda, "nfe_cancelamento_codigo", None)
    motivo = getattr(venda, "nfe_cancelamento_motivo", None)
    solicitado_em = getattr(venda, "nfe_cancelamento_solicitado_em", None)
    return {
        "cancelamento_status": status,
        "cancelamento_codigo": codigo if isinstance(codigo, str) else None,
        "cancelamento_motivo": motivo if isinstance(motivo, str) else None,
        "cancelamento_solicitado_em": safe_datetime_to_iso(solicitado_em)
        if isinstance(solicitado_em, datetime)
        else None,
        "cancelamento_solicitado": status == "solicitado",
        "pendencia_fiscal_cancelamento": pendencia,
        **campos_estorno(venda),
    }


def campos_estorno(venda):
    campos = {}
    for nome, tipo in (
        ("status", str),
        ("numero", int),
        ("serie", int),
        ("protocolo", str),
    ):
        valor = getattr(venda, f"nfe_estorno_{nome}", None)
        campos[f"nfe_estorno_{nome}"] = valor if type(valor) is tipo else None
    return campos


def campos_cancelamento_com_aliases(venda):
    campos = campos_cancelamento(venda)
    return {
        **campos,
        **{
            f"nfe_{nome}": campos[nome]
            for nome in (
                "cancelamento_status",
                "cancelamento_codigo",
                "cancelamento_motivo",
                "cancelamento_solicitado_em",
            )
        },
    }
