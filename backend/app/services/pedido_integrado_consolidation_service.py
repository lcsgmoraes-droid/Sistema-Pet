from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.pedido_integrado_models import PedidoIntegrado


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def numero_pedido_loja_do_payload(payload_or_pedido: Any) -> str | None:
    payload = _dict(getattr(payload_or_pedido, "payload", payload_or_pedido))
    pedido_payload = _dict(payload.get("pedido"))
    webhook_payload = _dict(payload.get("webhook"))

    for candidato in (
        pedido_payload.get("numeroPedidoLoja"),
        pedido_payload.get("numeroLoja"),
        pedido_payload.get("numeroPedido"),
        webhook_payload.get("numeroPedidoLoja"),
        webhook_payload.get("numeroLoja"),
        payload.get("numeroPedidoLoja"),
        payload.get("numeroLoja"),
    ):
        texto = _text(candidato)
        if texto:
            return texto
    return None


def loja_id_do_payload(payload_or_pedido: Any) -> str | None:
    payload = _dict(getattr(payload_or_pedido, "payload", payload_or_pedido))
    pedido_payload = _dict(payload.get("pedido"))
    webhook_payload = _dict(payload.get("webhook"))
    pedido_loja = _dict(pedido_payload.get("loja"))
    webhook_loja = _dict(webhook_payload.get("loja"))
    loja_virtual = _dict(pedido_payload.get("lojaVirtual"))

    return _text(
        pedido_loja.get("id")
        or webhook_loja.get("id")
        or loja_virtual.get("id")
        or pedido_payload.get("loja_id")
        or webhook_payload.get("loja_id")
    )


def ultima_nf_do_payload(payload_or_pedido: Any) -> dict:
    payload = _dict(getattr(payload_or_pedido, "payload", payload_or_pedido))
    pedido_payload = _dict(payload.get("pedido"))
    return _dict(
        payload.get("ultima_nf")
        or pedido_payload.get("notaFiscal")
        or pedido_payload.get("nota")
        or pedido_payload.get("nfe")
    )


def pedido_tem_nf_deterministica(payload_or_pedido: Any) -> bool:
    ultima_nf = ultima_nf_do_payload(payload_or_pedido)
    nf_id = _text(ultima_nf.get("id") or ultima_nf.get("nfe_id"))
    nf_numero = _text(ultima_nf.get("numero"))
    return bool(nf_numero or (nf_id and nf_id not in {"0", "-1"}))


def pedido_mesclado_info(payload_or_pedido: Any) -> dict:
    payload = _dict(getattr(payload_or_pedido, "payload", payload_or_pedido))
    return _dict(payload.get("pedido_mesclado"))


def pedido_esta_mesclado(payload_or_pedido: Any) -> bool:
    return bool(_text(pedido_mesclado_info(payload_or_pedido).get("pedido_canonico_id")))


def pedido_canonico_id_mescla(payload_or_pedido: Any) -> int | None:
    try:
        value = pedido_mesclado_info(payload_or_pedido).get("pedido_canonico_id")
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def pedidos_alias_bling_do_payload(payload_or_pedido: Any) -> list[dict]:
    payload = _dict(getattr(payload_or_pedido, "payload", payload_or_pedido))
    aliases = payload.get("pedidos_bling_aliases")
    return aliases if isinstance(aliases, list) else []


def registrar_alias_bling_no_payload(
    payload_or_pedido: Any,
    *,
    pedido_bling_id: str | None,
    pedido_bling_numero: str | None,
    numero_pedido_loja: str | None,
    loja_id: str | None,
    merged_at: datetime | None = None,
    motivo: str = "numero_pedido_loja_duplicado",
) -> dict:
    payload = dict(_dict(getattr(payload_or_pedido, "payload", payload_or_pedido)))
    pedido_bling_id = _text(pedido_bling_id)
    pedido_bling_numero = _text(pedido_bling_numero)
    numero_pedido_loja = _text(numero_pedido_loja)
    loja_id = _text(loja_id)

    if not pedido_bling_id and not pedido_bling_numero:
        return payload

    aliases = list(pedidos_alias_bling_do_payload(payload))
    chave_nova = (pedido_bling_id, pedido_bling_numero, numero_pedido_loja, loja_id)
    chaves_existentes = {
        (
            _text(item.get("pedido_bling_id")),
            _text(item.get("pedido_bling_numero")),
            _text(item.get("numero_pedido_loja")),
            _text(item.get("loja_id")),
        )
        for item in aliases
        if isinstance(item, dict)
    }
    if chave_nova not in chaves_existentes:
        aliases.append(
            {
                "pedido_bling_id": pedido_bling_id,
                "pedido_bling_numero": pedido_bling_numero,
                "numero_pedido_loja": numero_pedido_loja,
                "loja_id": loja_id,
                "merged_at": merged_at.isoformat() if isinstance(merged_at, datetime) else None,
                "motivo": motivo,
            }
        )
    payload["pedidos_bling_aliases"] = aliases
    return payload


def marcar_payload_como_mesclado(
    payload_or_pedido: Any,
    *,
    pedido_canonico: PedidoIntegrado,
    numero_pedido_loja: str | None,
    loja_id: str | None,
    merged_at: datetime | None = None,
    motivo: str = "numero_pedido_loja_duplicado",
) -> dict:
    payload = dict(_dict(getattr(payload_or_pedido, "payload", payload_or_pedido)))
    payload["pedido_mesclado"] = {
        "pedido_canonico_id": getattr(pedido_canonico, "id", None),
        "pedido_canonico_bling_id": _text(getattr(pedido_canonico, "pedido_bling_id", None)),
        "pedido_canonico_bling_numero": _text(getattr(pedido_canonico, "pedido_bling_numero", None)),
        "numero_pedido_loja": _text(numero_pedido_loja),
        "loja_id": _text(loja_id),
        "merged_at": merged_at.isoformat() if isinstance(merged_at, datetime) else None,
        "motivo": motivo,
    }
    return payload


def _ordem_preferencia_pedido(pedido: PedidoIntegrado) -> tuple:
    status = _text(getattr(pedido, "status", None))
    status_rank = {
        "confirmado": 3,
        "aberto": 2,
        "expirado": 1,
        "cancelado": 0,
        "mesclado": -1,
    }.get(status, 0)
    created_at = getattr(pedido, "created_at", None) or getattr(pedido, "criado_em", None)
    if isinstance(created_at, datetime):
        created_key = -(
            created_at.toordinal() * 86400
            + created_at.hour * 3600
            + created_at.minute * 60
            + created_at.second
        )
    else:
        created_key = 0
    return (
        0 if pedido_esta_mesclado(pedido) else 1,
        1 if pedido_tem_nf_deterministica(pedido) else 0,
        status_rank,
        created_key,
        -int(getattr(pedido, "id", 0) or 0),
    )


def escolher_pedido_canonico(candidatos: list[PedidoIntegrado]) -> PedidoIntegrado | None:
    validos = [pedido for pedido in candidatos if pedido is not None]
    if not validos:
        return None
    return max(validos, key=_ordem_preferencia_pedido)


def resolver_pedido_canonico(db: Session, pedido: PedidoIntegrado | None) -> PedidoIntegrado | None:
    atual = pedido
    visitados: set[int] = set()
    while atual and pedido_esta_mesclado(atual):
        if getattr(atual, "id", None) in visitados:
            break
        visitados.add(int(getattr(atual, "id", 0) or 0))
        pedido_canonico_id = pedido_canonico_id_mescla(atual)
        if not pedido_canonico_id:
            break
        atual = (
            db.query(PedidoIntegrado)
            .filter(
                PedidoIntegrado.id == pedido_canonico_id,
                PedidoIntegrado.tenant_id == atual.tenant_id,
            )
            .first()
        )
    return atual


def localizar_pedido_por_bling_id(
    db: Session,
    *,
    tenant_id,
    pedido_bling_id: str | None,
    resolver_mescla: bool = True,
) -> PedidoIntegrado | None:
    pedido_bling_id = _text(pedido_bling_id)
    if not pedido_bling_id:
        return None

    query = db.query(PedidoIntegrado).filter(PedidoIntegrado.pedido_bling_id == pedido_bling_id)
    if tenant_id is not None:
        query = query.filter(PedidoIntegrado.tenant_id == tenant_id)
    pedido = query.first()
    if pedido and resolver_mescla:
        return resolver_pedido_canonico(db, pedido)
    return pedido


def listar_pedidos_por_numero_loja(
    db: Session,
    *,
    tenant_id,
    numero_pedido_loja: str | None,
    loja_id: str | None = None,
    limite_scan: int = 2000,
    incluir_mesclados: bool = False,
) -> list[PedidoIntegrado]:
    numero = _text(numero_pedido_loja)
    if not numero:
        return []

    loja_id = _text(loja_id)
    pedidos = (
        db.query(PedidoIntegrado)
        .filter(PedidoIntegrado.tenant_id == tenant_id)
        .order_by(PedidoIntegrado.created_at.desc(), PedidoIntegrado.id.desc())
        .limit(max(int(limite_scan or 0), 1))
        .all()
    )

    candidatos = []
    for pedido in pedidos:
        if not incluir_mesclados and pedido_esta_mesclado(pedido):
            continue
        if numero_pedido_loja_do_payload(pedido) != numero:
            continue
        if loja_id and loja_id_do_payload(pedido) not in {None, loja_id}:
            continue
        candidatos.append(pedido)
    return candidatos


def localizar_pedido_canonico_por_numero_loja(
    db: Session,
    *,
    tenant_id,
    numero_pedido_loja: str | None,
    loja_id: str | None = None,
    limite_scan: int = 2000,
) -> PedidoIntegrado | None:
    candidatos = listar_pedidos_por_numero_loja(
        db,
        tenant_id=tenant_id,
        numero_pedido_loja=numero_pedido_loja,
        loja_id=loja_id,
        limite_scan=limite_scan,
        incluir_mesclados=False,
    )
    return escolher_pedido_canonico(candidatos)
