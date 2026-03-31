from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from time import monotonic, sleep
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, configure_mappers

from app.bling_flow_monitor_models import BlingFlowEvent, BlingFlowIncident
from app.db import SessionLocal
from app.nfe_cache_models import BlingNotaFiscalCache
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao, Produto
from app.utils.logger import logger


SEVERITY_RANK = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

FINAL_STATUS = {"confirmado", "cancelado", "expirado"}
OPEN_INCIDENT_STATUSES = {"open", "ignored"}
MONITORED_INCIDENT_CODES = {
    "PEDIDO_SEM_ITENS",
    "SKU_SEM_PRODUTO_LOCAL",
    "RESERVA_ATIVA_EM_PEDIDO_FINALIZADO",
    "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
    "ITEM_VENDIDO_EM_PEDIDO_ABERTO",
    "NF_AUTORIZADA_PEDIDO_NAO_CONFIRMADO",
    "NF_ENCONTRADA_SEM_VINCULO_NO_PEDIDO",
    "NF_ENCONTRADA_COM_DIVERGENCIA_NO_PEDIDO",
    "NF_MULTIPLA_ENCONTRADA_POR_PEDIDO_LOJA",
    "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
    "SKU_MAPEADO_POR_CODIGO_BARRAS",
}
NF_AUTHORIZED_CODES = {2, 5, 9}
_NF_RECENTES_CACHE_SECONDS = 300
_NF_RECENTES_ENRICH_LIMIT = 60
_NF_RECENTES_ENRICH_DELAY_SECONDS = 0.35
_nf_recentes_cache: dict[tuple[str, int], dict] = {}


def _garantir_registry_sqlalchemy_auditoria() -> None:
    # A auditoria pode rodar fora do app.main (script/scheduler/manual),
    # então ela precisa bootstrapar explicitamente os modelos com relacionamentos
    # declarados por string antes de qualquer query.
    import app.models  # noqa: F401
    import app.financeiro_models  # noqa: F401
    import app.dre_plano_contas_models  # noqa: F401
    import app.ia.aba7_extrato_models  # noqa: F401
    import app.ia.aba7_models  # noqa: F401

    configure_mappers()


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


def _nf_bling_id_valido(value: Any) -> str | None:
    texto = _text(value)
    if not texto or texto in {"0", "-1"}:
        return None
    return texto


def registrar_vinculo_nf_pedido(
    *,
    pedido: PedidoIntegrado,
    source: str,
    nf_bling_id: str | None = None,
    nf_numero: str | None = None,
    status: str = "ok",
    severity: str = "info",
    message: str | None = None,
    payload: dict | None = None,
    processed_at: Any = None,
    db: Session | None = None,
    auto_fix_applied: bool = False,
) -> int | None:
    payload_extra = _dict(_json_safe(payload or {}))
    nf_contexto = _ultima_nf(getattr(pedido, "payload", None))
    payload_base = {
        "pedido_bling_numero": _text(getattr(pedido, "pedido_bling_numero", None)),
        "numero_pedido_loja": _numero_pedido_loja_pedido(pedido),
        "pedido_status_atual": _text(getattr(pedido, "status", None)),
        "nf_numero": _text(nf_numero) or _text(nf_contexto.get("numero")),
    }
    return registrar_evento(
        tenant_id=pedido.tenant_id,
        source=source,
        event_type="invoice.linked_to_order",
        entity_type="nf",
        status=status,
        severity=severity,
        message=message or "NF vinculada ao pedido durante o processamento do evento",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido.pedido_bling_id,
        nf_bling_id=_nf_bling_id_valido(nf_bling_id) or _nf_bling_id_valido(nf_contexto.get("id")),
        payload={**payload_base, **payload_extra},
        processed_at=processed_at,
        db=db,
        auto_fix_applied=auto_fix_applied,
    )


def _build_incident_key(
    code: str,
    *,
    pedido_integrado_id: int | None = None,
    pedido_bling_id: str | None = None,
    nf_bling_id: str | None = None,
    sku: str | None = None,
) -> str:
    parts = [
        code,
        str(pedido_integrado_id or ""),
        pedido_bling_id or "",
        _nf_bling_id_valido(nf_bling_id) or "",
        sku or "",
    ]
    return "|".join(parts)


def _pick_more_severe(current: str, incoming: str) -> str:
    if SEVERITY_RANK.get(incoming, 0) >= SEVERITY_RANK.get(current, 0):
        return incoming
    return current


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _ultima_nf(payload: dict | None) -> dict:
    payload = _dict(payload)
    pedido = _dict(payload.get("pedido"))
    return _dict(
        payload.get("ultima_nf")
        or pedido.get("notaFiscal")
        or pedido.get("nota")
        or pedido.get("nfe")
    )


def _nf_autorizada(payload: dict | None) -> bool:
    nf = _ultima_nf(payload)
    return _nf_contexto_autorizado(nf)


def _nf_contexto_autorizado(nf: dict | None) -> bool:
    nf = _dict(nf)
    codigo = nf.get("situacao_codigo")
    try:
        if codigo is not None and int(codigo) in NF_AUTHORIZED_CODES:
            return True
    except (TypeError, ValueError):
        pass

    situacao = (nf.get("situacao") or nf.get("status") or "").strip().lower()
    return any(token in situacao for token in ("autoriz", "emitida", "emitido"))


def _numero_pedido_loja_pedido(pedido: PedidoIntegrado | None) -> str | None:
    payload = _dict(getattr(pedido, "payload", None))
    pedido_payload = _dict(payload.get("pedido"))
    webhook_payload = _dict(payload.get("webhook"))

    for candidato in (
        pedido_payload.get("numeroLoja"),
        pedido_payload.get("numeroPedidoLoja"),
        pedido_payload.get("numeroPedido"),
        webhook_payload.get("numeroLoja"),
        webhook_payload.get("numeroPedidoLoja"),
        payload.get("numeroLoja"),
        payload.get("numeroPedidoLoja"),
    ):
        texto = _text(candidato)
        if texto:
            return texto
    return None


def _loja_id_pedido_integrado(pedido: PedidoIntegrado | None) -> str | None:
    payload = _dict(getattr(pedido, "payload", None))
    pedido_payload = _dict(payload.get("pedido"))
    webhook_payload = _dict(payload.get("webhook"))
    pedido_loja = _dict(pedido_payload.get("loja"))
    webhook_loja = _dict(webhook_payload.get("loja"))
    loja_virtual = _dict(pedido_payload.get("lojaVirtual"))

    return _text(
        _primeiro_preenchido(
            pedido_loja.get("id"),
            webhook_loja.get("id"),
            loja_virtual.get("id"),
            pedido_payload.get("loja_id"),
            webhook_payload.get("loja_id"),
        )
    )


def _loja_id_nf_contexto(nf_contexto: dict | None) -> str | None:
    nf_contexto = _dict(nf_contexto)
    loja = _dict(nf_contexto.get("loja"))
    return _text(_primeiro_preenchido(nf_contexto.get("loja_id"), loja.get("id")))


def _canal_pedido_integrado(pedido: PedidoIntegrado | None) -> str | None:
    if not pedido:
        return None

    try:
        from app.integracao_bling_pedido_routes import _resolver_canal_pedido

        canal, _, _ = _resolver_canal_pedido(
            _dict(getattr(pedido, "payload", None)),
            getattr(pedido, "canal", None),
        )
        return _text(canal)
    except Exception:
        return _text(getattr(pedido, "canal", None))


def _canal_label_nf_contexto(data: dict | None) -> tuple[str | None, str | None]:
    data = _dict(data)
    if not data:
        return None, None

    try:
        from app.nfe_routes import _normalizar_resumo_canal

        resumo = _normalizar_resumo_canal(data)
        return _text(resumo.get("canal")), _text(resumo.get("canal_label"))
    except Exception:
        return None, None


def _pedido_total(pedido: PedidoIntegrado | None) -> float | None:
    payload = _dict(getattr(pedido, "payload", None))
    pedido_payload = _dict(payload.get("pedido"))
    financeiro = _dict(pedido_payload.get("financeiro"))
    ultima_nf = _ultima_nf(payload)

    for candidato in (
        ultima_nf.get("valor_total"),
        financeiro.get("total"),
        pedido_payload.get("total"),
        pedido_payload.get("valorTotal"),
        pedido_payload.get("valor_total"),
    ):
        try:
            valor = float(candidato)
            if valor > 0:
                return valor
        except (TypeError, ValueError):
            continue
    return None


def _resumir_nf_bling_recente(item: dict, modelo: int) -> dict:
    item = _dict(item)
    try:
        from app.integracao_bling_nf_routes import _extrair_numero_pedido_loja_nf
    except Exception:
        numero_pedido_loja = None
    else:
        numero_pedido_loja = _extrair_numero_pedido_loja_nf(item)

    pedido_ref = _dict(item.get("pedido") or item.get("pedidoVenda") or item.get("pedidoCompra"))
    canal, canal_label = _canal_label_nf_contexto(item)

    return {
        "id": _text(item.get("id")),
        "numero": _text(item.get("numero")),
        "serie": _text(item.get("serie")),
        "modelo": modelo,
        "situacao_codigo": _coerce_int(item.get("situacao"), 0),
        "situacao": _text(item.get("descricaoSituacao") or item.get("situacao")),
        "chave": _text(item.get("chaveAcesso") or item.get("chave")),
        "valor_total": item.get("valorNota") or item.get("valorTotalNf") or item.get("valorTotal") or item.get("valor_total"),
        "data_emissao": _text(item.get("dataEmissao") or item.get("data_emissao") or item.get("data")),
        "numero_pedido_loja": _text(numero_pedido_loja),
        "loja_id": _loja_id_nf_contexto(item),
        "pedido_bling_id": _text(pedido_ref.get("id")),
        "pedido_bling_numero": _text(pedido_ref.get("numero")),
        "canal": canal,
        "canal_label": canal_label,
    }


def _enriquecer_resumo_nf_com_relacao(resumo: dict) -> dict:
    resumo = _dict(resumo)
    nf_id = _text(resumo.get("id"))
    if not nf_id:
        return resumo

    try:
        from app.integracao_bling_nf_routes import _consultar_relacao_nf_bling

        relacao = _dict(
            _consultar_relacao_nf_bling(
                nf_id=nf_id,
                situacao_num=_coerce_int(resumo.get("situacao_codigo"), 0),
            )
        )
    except Exception as exc:
        logger.warning(f"[BLING FLOW MONITOR] Falha ao enriquecer NF recente {nf_id}: {exc}")
        return resumo

    nf_completa = _dict(relacao.get("nf_completa"))
    canal = _text(resumo.get("canal"))
    canal_label = _text(resumo.get("canal_label"))
    if nf_completa and (not canal or canal == "bling" or not canal_label):
        canal_nf, canal_label_nf = _canal_label_nf_contexto(nf_completa)
        canal = canal or canal_nf
        canal_label = canal_label or canal_label_nf

    valor_total = _primeiro_preenchido(
        resumo.get("valor_total"),
        nf_completa.get("valorNota"),
        nf_completa.get("valorTotalNf"),
        nf_completa.get("valorTotal"),
        nf_completa.get("valor_total"),
    )

    return {
        **resumo,
        "pedido_bling_id": _text(relacao.get("pedido_bling_id")) or _text(resumo.get("pedido_bling_id")),
        "pedido_bling_numero": _text(relacao.get("pedido_bling_numero")) or _text(resumo.get("pedido_bling_numero")),
        "numero_pedido_loja": _text(relacao.get("numero_pedido_loja")) or _text(resumo.get("numero_pedido_loja")),
        "loja_id": _loja_id_nf_contexto(nf_completa) or _text(resumo.get("loja_id")),
        "valor_total": valor_total,
        "canal": canal,
        "canal_label": canal_label,
    }


def _obter_nfs_recentes_cache_local(db: Session, *, tenant_id, dias: int) -> list[dict]:
    data_inicial = _utcnow() - timedelta(days=max(1, min(int(dias or 1), 15)))
    registros = (
        db.query(BlingNotaFiscalCache)
        .filter(
            BlingNotaFiscalCache.tenant_id == tenant_id,
            BlingNotaFiscalCache.data_emissao.isnot(None),
            BlingNotaFiscalCache.data_emissao >= data_inicial,
        )
        .order_by(BlingNotaFiscalCache.data_emissao.desc(), BlingNotaFiscalCache.id.desc())
        .limit(_NF_RECENTES_ENRICH_LIMIT * 3)
        .all()
    )
    notas: list[dict] = []
    ids_vistos: set[str] = set()
    for registro in registros:
        nf_id = _text(getattr(registro, "bling_id", None))
        if not nf_id or nf_id in ids_vistos:
            continue
        ids_vistos.add(nf_id)
        resumo = {
            "id": nf_id,
            "numero": _text(getattr(registro, "numero", None)),
            "serie": _text(getattr(registro, "serie", None)),
            "modelo": getattr(registro, "modelo", None),
            "situacao": _text(getattr(registro, "status", None)),
            "situacao_codigo": 5 if (_text(getattr(registro, "status", None)) or "").lower() == "autorizada" else 0,
            "chave": _text(getattr(registro, "chave", None)),
            "valor_total": getattr(registro, "valor", None),
            "data_emissao": getattr(registro, "data_emissao", None).isoformat() if getattr(registro, "data_emissao", None) else None,
            "numero_pedido_loja": _text(getattr(registro, "numero_pedido_loja", None)),
            "loja_id": _loja_id_nf_contexto(_dict(getattr(registro, "detalhe_payload", None)) or _dict(getattr(registro, "resumo_payload", None))),
            "pedido_bling_id": _text(getattr(registro, "pedido_bling_id_ref", None)),
            "pedido_bling_numero": _text(_dict(getattr(registro, "detalhe_payload", None)).get("pedido_bling_numero"))
            or _text(_dict(getattr(registro, "resumo_payload", None)).get("pedido_bling_numero")),
            "canal": _text(getattr(registro, "canal", None)),
            "canal_label": _text(getattr(registro, "canal_label", None)),
        }
        if resumo.get("numero_pedido_loja") or resumo.get("pedido_bling_numero"):
            notas.append(resumo)
    return notas


def _obter_nfs_recentes_bling(*, tenant_id, dias: int, db: Session | None = None) -> list[dict]:
    dias = max(1, min(int(dias or 1), 15))
    cache_key = (str(tenant_id or ""), dias)
    cache_atual = _nf_recentes_cache.get(cache_key)
    if cache_atual and (monotonic() - cache_atual.get("ts_monotonic", 0)) <= _NF_RECENTES_CACHE_SECONDS:
        return deepcopy(cache_atual.get("items") or [])

    notas_cache_local = _obter_nfs_recentes_cache_local(db, tenant_id=tenant_id, dias=dias) if db else []
    if notas_cache_local:
        _nf_recentes_cache[cache_key] = {
            "ts_monotonic": monotonic(),
            "items": deepcopy(notas_cache_local),
        }
        return notas_cache_local

    from app.bling_integration import BlingAPI

    bling = BlingAPI()
    data_inicial = (_utcnow() - timedelta(days=dias)).date().isoformat()
    data_final = (_utcnow() + timedelta(days=1)).date().isoformat()
    notas: list[dict] = []
    ids_vistos: set[str] = set()

    for listar_fn, modelo in ((bling.listar_nfes, 55), (bling.listar_nfces, 65)):
        try:
            resposta = listar_fn(data_inicial=data_inicial, data_final=data_final)
        except Exception as exc:
            logger.warning(f"[BLING FLOW MONITOR] Falha ao listar notas recentes do Bling (modelo {modelo}): {exc}")
            continue

        for index, bruto in enumerate(_list(_dict(resposta).get("data"))):
            resumo = _resumir_nf_bling_recente(bruto, modelo)
            if index < _NF_RECENTES_ENRICH_LIMIT and not (
                resumo.get("numero_pedido_loja") or resumo.get("pedido_bling_numero")
            ):
                resumo = _enriquecer_resumo_nf_com_relacao(resumo)
                sleep(_NF_RECENTES_ENRICH_DELAY_SECONDS)
            nf_id = _text(resumo.get("id"))
            if not nf_id or nf_id in ids_vistos:
                continue
            ids_vistos.add(nf_id)
            if resumo.get("numero_pedido_loja") or resumo.get("pedido_bling_numero"):
                notas.append(resumo)

    _nf_recentes_cache[cache_key] = {
        "ts_monotonic": monotonic(),
        "items": deepcopy(notas),
    }
    return notas


def _indexar_nfs_por_pedido_loja(notas: list[dict]) -> dict[str, list[dict]]:
    mapa: dict[str, list[dict]] = {}
    for nf in notas:
        numero = _text(_dict(nf).get("numero_pedido_loja"))
        if not numero:
            continue
        mapa.setdefault(numero, [])
        if not any(_text(item.get("id")) == _text(_dict(nf).get("id")) for item in mapa[numero]):
            mapa[numero].append(_dict(nf))

    for numero, itens in mapa.items():
        itens.sort(
            key=lambda item: (
                1 if _nf_contexto_autorizado(item) else 0,
                _text(item.get("data_emissao")) or "",
                _coerce_int(item.get("numero"), 0),
                _coerce_int(item.get("id"), 0),
            ),
            reverse=True,
        )
        mapa[numero] = itens
    return mapa


def _nf_detectada_combina_com_pedido(pedido: PedidoIntegrado, nf_contexto: dict | None) -> tuple[bool, dict]:
    nf_contexto = _dict(nf_contexto)
    if not nf_contexto:
        return False, {"motivo": "nf_nao_informada"}

    numero_pedido_loja = _numero_pedido_loja_pedido(pedido)
    numero_nf = _text(nf_contexto.get("numero_pedido_loja"))
    if numero_pedido_loja and numero_nf and numero_pedido_loja != numero_nf:
        return False, {
            "motivo": "numero_pedido_loja_divergente",
            "pedido": numero_pedido_loja,
            "nf": numero_nf,
        }

    loja_id_pedido = _loja_id_pedido_integrado(pedido)
    loja_id_nf = _loja_id_nf_contexto(nf_contexto)
    if loja_id_pedido and loja_id_nf and loja_id_pedido != loja_id_nf:
        return False, {
            "motivo": "loja_divergente",
            "pedido": loja_id_pedido,
            "nf": loja_id_nf,
        }

    canal_pedido = _canal_pedido_integrado(pedido)
    canal_nf = _text(nf_contexto.get("canal"))
    if canal_pedido and canal_nf and canal_pedido != canal_nf:
        return False, {
            "motivo": "canal_divergente",
            "pedido": canal_pedido,
            "nf": canal_nf,
        }

    total_pedido = _pedido_total(pedido)
    try:
        total_nf = float(nf_contexto.get("valor_total"))
    except (TypeError, ValueError):
        total_nf = None
    if total_pedido and total_nf and abs(total_pedido - total_nf) > 0.05:
        return False, {
            "motivo": "valor_total_divergente",
            "pedido": total_pedido,
            "nf": total_nf,
        }

    return True, {
        "numero_pedido_loja": numero_pedido_loja,
        "loja_id": loja_id_pedido,
        "canal": canal_pedido,
        "total_pedido": total_pedido,
        "total_nf": total_nf,
    }


def _produto_por_sku(db: Session, tenant_id, sku: str) -> tuple[Produto | None, str | None]:
    if not sku:
        return None, None

    produto = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            or_(Produto.codigo == sku, Produto.codigo_barras == sku),
        )
        .first()
    )
    if not produto:
        return None, None
    if produto.codigo == sku:
        return produto, "codigo"
    if produto.codigo_barras == sku:
        return produto, "codigo_barras"
    return produto, "desconhecido"


def _contar_movimentacoes_saida_nf(
    db: Session,
    pedido: PedidoIntegrado,
    *,
    payload: dict | None,
) -> tuple[int, int]:
    from app.services.bling_nf_service import movimento_documentado_por_nf

    nf = _ultima_nf(payload)
    nf_id = _text(_primeiro_preenchido(nf.get("id"), nf.get("nfe_id")))
    nf_numero = _text(nf.get("numero"))
    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == pedido.tenant_id,
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.referencia_id == pedido.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .all()
    )
    total = len(movimentacoes)
    total_nf = sum(
        1
        for mov in movimentacoes
        if movimento_documentado_por_nf(mov, nf_numero=nf_numero, nf_bling_id=nf_id)
    )
    return total, total_nf


def _make_incident(
    code: str,
    *,
    severity: str,
    title: str,
    message: str,
    suggested_action: str,
    auto_fixable: bool,
    pedido: PedidoIntegrado,
    sku: str | None = None,
    nf_bling_id: str | None = None,
    details: dict | None = None,
) -> dict:
    detalhes = _dict(_json_safe(details or {}))
    nf_detectada = _dict(detalhes.get("nf_detectada"))
    nf_payload = _ultima_nf(_dict(getattr(pedido, "payload", None)))
    nf_numero = _text(
        _primeiro_preenchido(
            detalhes.get("nf_numero"),
            nf_detectada.get("numero"),
            nf_payload.get("numero"),
        )
    )
    if nf_numero:
        detalhes["nf_numero"] = nf_numero

    return {
        "code": code,
        "severity": severity,
        "title": title,
        "message": message,
        "suggested_action": suggested_action,
        "auto_fixable": auto_fixable,
        "pedido_integrado_id": pedido.id,
        "pedido_bling_id": _text(pedido.pedido_bling_id),
        "nf_bling_id": _nf_bling_id_valido(nf_bling_id),
        "sku": _text(sku),
        "details": detalhes,
    }


def diagnosticar_pedido_integrado(
    pedido,
    itens,
    payload: dict | None,
    *,
    movimentacoes_saida: int,
    movimentacoes_saida_nf: int | None = None,
    itens_sem_produto: list[dict] | None = None,
    itens_mapeados_por_barra: list[dict] | None = None,
    nf_detectada: dict | None = None,
    nfs_detectadas: list[dict] | None = None,
) -> list[dict]:
    itens_sem_produto = itens_sem_produto or []
    itens_mapeados_por_barra = itens_mapeados_por_barra or []
    incidentes: list[dict] = []
    nf = _ultima_nf(payload)
    nf_detectada = _dict(nf_detectada)
    nfs_detectadas = [_dict(item) for item in (nfs_detectadas or []) if isinstance(item, dict)]
    nf_auditavel = nf
    if not _nf_contexto_autorizado(nf) and len(nfs_detectadas) == 1 and _nf_contexto_autorizado(nfs_detectadas[0]):
        nf_auditavel = nfs_detectadas[0]
    nf_local_id = _text(nf.get("id"))
    nf_local_numero = _text(nf.get("numero"))
    movimentacoes_saida_nf = movimentacoes_saida if movimentacoes_saida_nf is None else int(movimentacoes_saida_nf)

    if not itens:
        incidentes.append(
            _make_incident(
                "PEDIDO_SEM_ITENS",
                severity="high",
                title="Pedido sem itens importados",
                message="O pedido foi registrado, mas nenhum item ficou salvo no sistema.",
                suggested_action="Reconsultar o pedido no Bling e recriar os itens/reservas.",
                auto_fixable=True,
                pedido=pedido,
                nf_bling_id=_text(nf.get("id")),
            )
        )

    for item_info in itens_sem_produto:
        sku = _text(item_info.get("sku"))
        incidentes.append(
            _make_incident(
                "SKU_SEM_PRODUTO_LOCAL",
                severity="critical",
                title="SKU sem produto local",
                message=f"O SKU '{sku}' do pedido nao foi encontrado no cadastro local.",
                suggested_action="Tentar autocadastro pelo Bling ou revisar o SKU do item.",
                auto_fixable=True,
                pedido=pedido,
                sku=sku,
                nf_bling_id=_text(nf.get("id")),
                details=item_info,
            )
        )

    for item_info in itens_mapeados_por_barra:
        sku = _text(item_info.get("sku"))
        incidentes.append(
            _make_incident(
                "SKU_MAPEADO_POR_CODIGO_BARRAS",
                severity="medium",
                title="SKU conciliado por codigo de barras",
                message=f"O item '{sku}' foi conciliado pelo codigo de barras, nao pelo SKU principal.",
                suggested_action="Revisar o padrao de SKU entre Bling e cadastro local para evitar divergencias.",
                auto_fixable=False,
                pedido=pedido,
                sku=sku,
                nf_bling_id=_text(nf.get("id")),
                details=item_info,
            )
        )

    itens_vendidos = [item for item in itens if getattr(item, "vendido_em", None)]

    if pedido.status == "confirmado" and _nf_contexto_autorizado(nf_auditavel):
        for item in itens:
            if not getattr(item, "vendido_em", None):
                incidentes.append(
                    _make_incident(
                        "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
                        severity="critical",
                        title="Pedido confirmado com item nao vendido",
                        message=f"O pedido esta confirmado, mas o item '{item.sku}' ainda nao foi consolidado como venda.",
                        suggested_action="Reconciliar o pedido confirmado e aplicar a baixa pendente.",
                        auto_fixable=True,
                        pedido=pedido,
                        sku=_text(item.sku),
                        nf_bling_id=_text(_primeiro_preenchido(nf_auditavel.get("id"), nf.get("id"))),
                    )
                )

        if itens_vendidos and movimentacoes_saida_nf < len(itens_vendidos):
            incidentes.append(
                _make_incident(
                    "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
                    severity="critical",
                    title="Pedido confirmado sem baixa completa de estoque",
                    message=(
                        f"Existem {len(itens_vendidos)} item(ns) vendidos, mas apenas "
                        f"{movimentacoes_saida_nf} movimentacao(oes) de saida vinculada(s) a NF atual."
                    ),
                    suggested_action="Reconciliar as baixas pendentes do pedido confirmado.",
                    auto_fixable=True,
                    pedido=pedido,
                    nf_bling_id=_text(_primeiro_preenchido(nf_auditavel.get("id"), nf.get("id"))),
                    details={
                        "nf_detectada": _json_safe(nf_auditavel),
                        "itens_vendidos": len(itens_vendidos),
                        "movimentacoes_saida": movimentacoes_saida,
                        "movimentacoes_saida_nf": movimentacoes_saida_nf,
                    },
                )
            )

    if pedido.status in {"cancelado", "expirado"}:
        for item in itens:
            if not getattr(item, "liberado_em", None) and not getattr(item, "vendido_em", None):
                incidentes.append(
                    _make_incident(
                        "RESERVA_ATIVA_EM_PEDIDO_FINALIZADO",
                        severity="high",
                        title="Reserva ativa em pedido finalizado",
                        message=f"O item '{item.sku}' segue reservado em um pedido {pedido.status}.",
                        suggested_action="Liberar a reserva logica remanescente.",
                        auto_fixable=True,
                        pedido=pedido,
                        sku=_text(item.sku),
                        nf_bling_id=_text(nf.get("id")),
                    )
                )

    if pedido.status in {"aberto", "expirado"}:
        for item in itens_vendidos:
            incidentes.append(
                _make_incident(
                    "ITEM_VENDIDO_EM_PEDIDO_ABERTO",
                    severity="critical",
                    title="Item vendido em pedido ainda aberto",
                    message=f"O item '{item.sku}' aparece vendido, mas o pedido segue como {pedido.status}.",
                    suggested_action="Revisar o status do pedido e reconciliar a baixa aplicando o estado correto.",
                    auto_fixable=False,
                    pedido=pedido,
                    sku=_text(item.sku),
                    nf_bling_id=_text(nf.get("id")),
                )
            )

    if pedido.status in {"aberto", "expirado"} and nfs_detectadas:
        nfs_distintas = {
            (_text(item.get("id")) or "", _text(item.get("numero")) or ""): item
            for item in nfs_detectadas
        }
        nfs_encontradas = list(nfs_distintas.values())
        if len(nfs_encontradas) > 1:
            incidentes.append(
                _make_incident(
                    "NF_MULTIPLA_ENCONTRADA_POR_PEDIDO_LOJA",
                    severity="high",
                    title="Multiplas NFs encontradas para o mesmo pedido na loja",
                    message=(
                        "Foi encontrada mais de uma NF recente no Bling usando o mesmo numero do pedido na loja. "
                        "A conciliacao automatica foi bloqueada para evitar vinculo incorreto."
                    ),
                    suggested_action="Abrir o pedido e as NFs relacionadas para confirmar manualmente qual nota deve ser vinculada.",
                    auto_fixable=False,
                    pedido=pedido,
                    details={
                        "numero_pedido_loja": _numero_pedido_loja_pedido(pedido),
                        "nfs": _json_safe(nfs_encontradas),
                    },
                )
            )
        else:
            nf_detectada = nfs_encontradas[0]
            nf_detectada_id = _text(nf_detectada.get("id"))
            nf_detectada_numero = _text(nf_detectada.get("numero"))
            nf_ja_vinculada = bool(
                (nf_local_id and nf_detectada_id and nf_local_id == nf_detectada_id)
                or (nf_local_numero and nf_detectada_numero and nf_local_numero == nf_detectada_numero)
            )

            if not nf_ja_vinculada:
                if _nf_detectada_combina_com_pedido(pedido, nf_detectada):
                    incidentes.append(
                        _make_incident(
                            "NF_ENCONTRADA_SEM_VINCULO_NO_PEDIDO",
                            severity="critical",
                            title="NF encontrada no Bling mas ainda nao vinculada ao pedido",
                            message=(
                                "Foi encontrada uma NF recente no Bling com o mesmo numero do pedido na loja, "
                                "mas o pedido local ainda nao recebeu esse vinculo nem os efeitos de confirmacao."
                            ),
                            suggested_action="Vincular a NF detectada ao pedido e executar a reconciliacao automatica do estoque.",
                            auto_fixable=True,
                            pedido=pedido,
                            nf_bling_id=nf_detectada_id,
                            details={"nf_detectada": _json_safe(nf_detectada)},
                        )
                    )
                else:
                    incidentes.append(
                        _make_incident(
                            "NF_ENCONTRADA_COM_DIVERGENCIA_NO_PEDIDO",
                            severity="high",
                            title="NF encontrada com divergencia de contexto do pedido",
                            message=(
                                "Uma NF recente foi encontrada pelo numero do pedido na loja, mas ha divergencia "
                                "de canal ou total entre o pedido local e a nota detectada."
                            ),
                            suggested_action="Comparar o pedido e a NF antes de vincular manualmente.",
                            auto_fixable=False,
                            pedido=pedido,
                            nf_bling_id=nf_detectada_id,
                            details={
                                "numero_pedido_loja": _numero_pedido_loja_pedido(pedido),
                                "canal_pedido": _canal_pedido_integrado(pedido),
                                "total_pedido": _pedido_total(pedido),
                                "nf_detectada": _json_safe(nf_detectada),
                            },
                        )
                    )

    if _nf_autorizada(payload) and pedido.status != "confirmado":
        incidentes.append(
            _make_incident(
                "NF_AUTORIZADA_PEDIDO_NAO_CONFIRMADO",
                severity="critical",
                title="NF autorizada sem confirmacao do pedido",
                message="Existe NF autorizada vinculada ao pedido, mas o pedido local ainda nao esta confirmado.",
                suggested_action="Reconciliar o pedido como confirmado e baixar o estoque pendente.",
                auto_fixable=True,
                pedido=pedido,
                nf_bling_id=_text(nf.get("id")),
                details={"nf": _json_safe(nf)},
            )
        )

    return incidentes


def _vincular_nf_detectada_ao_pedido(
    db: Session,
    pedido: PedidoIntegrado,
    nf_detectada: dict | None,
) -> tuple[bool, dict]:
    nf_detectada = _dict(nf_detectada)
    nf_id = _text(nf_detectada.get("id"))
    if not nf_id:
        return False, {"motivo": "nf_detectada_sem_id"}

    try:
        situacao_num = _coerce_int(
            _primeiro_preenchido(
                nf_detectada.get("situacao_codigo"),
                nf_detectada.get("situacao"),
            ),
            0,
        )
        from app.integracao_bling_nf_routes import _consultar_relacao_nf_bling, _registrar_nf_no_pedido
        from app.services.bling_nf_service import processar_nf_autorizada, processar_nf_cancelada

        relacao = _consultar_relacao_nf_bling(nf_id=nf_id, situacao_num=situacao_num)
        dados_nf = _dict(relacao.get("nf_completa")) or nf_detectada
        _registrar_nf_no_pedido(
            pedido=pedido,
            data=dados_nf,
            nf_id=nf_id,
            situacao_num=situacao_num,
        )
        db.add(pedido)
        db.flush()

        itens = db.query(PedidoIntegradoItem).filter(
            PedidoIntegradoItem.pedido_integrado_id == pedido.id
        ).all()

        acao = None
        if _nf_contexto_autorizado(nf_detectada):
            acao = processar_nf_autorizada(db=db, pedido=pedido, itens=itens, nf_id=nf_id)
        elif situacao_num == 4:
            acao = processar_nf_cancelada(db=db, pedido=pedido, itens=itens)

        registrar_vinculo_nf_pedido(
            pedido=pedido,
            source="autofix",
            nf_bling_id=nf_id,
            nf_numero=_text(dados_nf.get("numero")) or _text(nf_detectada.get("numero")),
            message="NF detectada pela auditoria foi vinculada automaticamente ao pedido",
            payload={
                "link_source": "auditoria",
                "nf": _json_safe(nf_detectada),
                "acao": _json_safe(acao),
            },
            db=db,
            auto_fix_applied=True,
        )
        return True, {
            "pedido_id": pedido.id,
            "pedido_bling_numero": pedido.pedido_bling_numero,
            "numero_pedido_loja": _numero_pedido_loja_pedido(pedido),
            "nf_id": nf_id,
            "nf_numero": _text(dados_nf.get("numero")) or _text(nf_detectada.get("numero")),
            "acao": _json_safe(acao),
        }
    except Exception as exc:
        return False, {"motivo": "falha_vinculo_nf_detectada", "erro": str(exc)}


def registrar_evento(
    *,
    tenant_id,
    source: str,
    event_type: str,
    entity_type: str = "pedido",
    status: str = "ok",
    severity: str = "info",
    message: str | None = None,
    error_message: str | None = None,
    pedido_integrado_id: int | None = None,
    pedido_bling_id: str | None = None,
    nf_bling_id: str | None = None,
    sku: str | None = None,
    payload: dict | None = None,
    auto_fix_applied: bool = False,
    processed_at: Any = None,
    db: Session | None = None,
) -> int | None:
    own_session = db is None
    session = db or SessionLocal()

    try:
        evento = BlingFlowEvent(
            tenant_id=tenant_id,
            source=source,
            event_type=event_type,
            entity_type=entity_type,
            status=status,
            severity=severity,
            message=message,
            error_message=error_message,
            pedido_integrado_id=pedido_integrado_id,
            pedido_bling_id=_text(pedido_bling_id),
            nf_bling_id=_nf_bling_id_valido(nf_bling_id),
            sku=_text(sku),
            payload=_json_safe(payload or {}),
            auto_fix_applied=auto_fix_applied,
            processed_at=normalizar_data_evento_monitor(processed_at) or _utcnow(),
        )
        session.add(evento)
        if own_session:
            session.commit()
            session.refresh(evento)
        else:
            session.flush()
        return getattr(evento, "id", None)
    except Exception as exc:
        if own_session:
            session.rollback()
        logger.warning(f"[BLING FLOW MONITOR] Falha ao registrar evento {event_type}: {exc}")
        return None
    finally:
        if own_session:
            session.close()


def abrir_incidente(
    *,
    tenant_id,
    code: str,
    severity: str,
    title: str,
    message: str,
    suggested_action: str,
    auto_fixable: bool,
    pedido_integrado_id: int | None = None,
    pedido_bling_id: str | None = None,
    nf_bling_id: str | None = None,
    sku: str | None = None,
    details: dict | None = None,
    source: str = "auditoria",
    scope: str = "pedido",
    db: Session | None = None,
) -> BlingFlowIncident | None:
    own_session = db is None
    session = db or SessionLocal()
    dedupe_key = _build_incident_key(
        code,
        pedido_integrado_id=pedido_integrado_id,
        pedido_bling_id=pedido_bling_id,
        nf_bling_id=nf_bling_id,
        sku=sku,
    )

    try:
        incidente = (
            session.query(BlingFlowIncident)
            .filter(
                BlingFlowIncident.tenant_id == tenant_id,
                BlingFlowIncident.dedupe_key == dedupe_key,
                BlingFlowIncident.status.in_(OPEN_INCIDENT_STATUSES),
            )
            .order_by(BlingFlowIncident.id.desc())
            .first()
        )

        agora = _utcnow()
        if incidente:
            incidente.last_seen_em = agora
            incidente.occurrences = int(incidente.occurrences or 0) + 1
            incidente.severity = _pick_more_severe(incidente.severity, severity)
            incidente.title = title
            incidente.message = message
            incidente.suggested_action = suggested_action
            incidente.auto_fixable = auto_fixable
            incidente.nf_bling_id = _nf_bling_id_valido(nf_bling_id)
            incidente.details = _json_safe(details or {})
            incidente.auto_fix_status = "pending" if auto_fixable else "manual"
        else:
            incidente = BlingFlowIncident(
                tenant_id=tenant_id,
                code=code,
                severity=severity,
                status="open",
                source=source,
                scope=scope,
                title=title,
                message=message,
                suggested_action=suggested_action,
                auto_fixable=auto_fixable,
                auto_fix_status="pending" if auto_fixable else "manual",
                dedupe_key=dedupe_key,
                pedido_integrado_id=pedido_integrado_id,
                pedido_bling_id=_text(pedido_bling_id),
                nf_bling_id=_nf_bling_id_valido(nf_bling_id),
                sku=_text(sku),
                details=_json_safe(details or {}),
                first_seen_em=agora,
                last_seen_em=agora,
                occurrences=1,
            )
            session.add(incidente)

        if own_session:
            session.commit()
            session.refresh(incidente)
        else:
            session.flush()
        return incidente
    except Exception as exc:
        if own_session:
            session.rollback()
        logger.warning(f"[BLING FLOW MONITOR] Falha ao abrir incidente {code}: {exc}")
        return None
    finally:
        if own_session:
            session.close()


def resolver_incidente_por_id(
    db: Session,
    tenant_id,
    incidente_id: int,
    *,
    resolution_note: str | None = None,
) -> BlingFlowIncident | None:
    incidente = (
        db.query(BlingFlowIncident)
        .filter(
            BlingFlowIncident.id == incidente_id,
            BlingFlowIncident.tenant_id == tenant_id,
        )
        .first()
    )
    if not incidente:
        return None

    incidente.status = "resolved"
    incidente.resolved_em = _utcnow()
    detalhes = _dict(incidente.details)
    if resolution_note:
        detalhes["resolution_note"] = resolution_note
    incidente.details = _json_safe(detalhes)
    db.add(incidente)
    db.commit()
    db.refresh(incidente)
    return incidente


def resolver_incidentes_relacionados(
    db: Session,
    *,
    tenant_id,
    codes: list[str] | tuple[str, ...] | set[str] | None = None,
    pedido_integrado_id: int | None = None,
    pedido_bling_id: str | None = None,
    nf_bling_id: str | None = None,
    resolution_note: str | None = None,
) -> int:
    query = db.query(BlingFlowIncident).filter(
        BlingFlowIncident.tenant_id == tenant_id,
        BlingFlowIncident.status.in_(OPEN_INCIDENT_STATUSES),
    )
    if codes:
        query = query.filter(BlingFlowIncident.code.in_(list(codes)))

    filtros = []
    if pedido_integrado_id:
        filtros.append(BlingFlowIncident.pedido_integrado_id == pedido_integrado_id)
    if pedido_bling_id:
        filtros.append(BlingFlowIncident.pedido_bling_id == _text(pedido_bling_id))
    if nf_bling_id:
        filtros.append(BlingFlowIncident.nf_bling_id == _text(nf_bling_id))
    if filtros:
        query = query.filter(or_(*filtros))

    resolvidos = 0
    for incidente in query.all():
        incidente.status = "resolved"
        incidente.resolved_em = _utcnow()
        detalhes = _dict(incidente.details)
        if resolution_note:
            detalhes["resolution_note"] = resolution_note
        incidente.details = _json_safe(detalhes)
        db.add(incidente)
        resolvidos += 1
    return resolvidos


def _resolver_incidentes_ausentes(
    db: Session,
    pedido: PedidoIntegrado,
    active_keys: set[str],
) -> int:
    incidentes = (
        db.query(BlingFlowIncident)
        .filter(
            BlingFlowIncident.tenant_id == pedido.tenant_id,
            BlingFlowIncident.source == "auditoria",
            BlingFlowIncident.status == "open",
            BlingFlowIncident.code.in_(list(MONITORED_INCIDENT_CODES)),
            or_(
                BlingFlowIncident.pedido_integrado_id == pedido.id,
                BlingFlowIncident.pedido_bling_id == pedido.pedido_bling_id,
            ),
        )
        .all()
    )

    resolvidos = 0
    for incidente in incidentes:
        if incidente.dedupe_key in active_keys:
            continue
        incidente.status = "resolved"
        incidente.resolved_em = _utcnow()
        db.add(incidente)
        resolvidos += 1
    return resolvidos


def _recarregar_itens_do_pedido(db: Session, pedido: PedidoIntegrado) -> tuple[bool, dict]:
    from app.bling_integration import BlingAPI
    from app.estoque_reserva_service import EstoqueReservaService

    pedido_completo = BlingAPI().consultar_pedido(pedido.pedido_bling_id)
    itens_bling = pedido_completo.get("itens") or []
    if not itens_bling:
        return False, {"motivo": "bling_sem_itens"}

    if not isinstance(pedido.payload, dict):
        pedido.payload = {}
    pedido.payload["pedido"] = pedido_completo

    existentes = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido.id
    ).count()
    if existentes:
        return True, {"itens_criados": 0, "motivo": "pedido_ja_possui_itens"}

    itens_criados = 0
    for item in itens_bling:
        sku = _text(item.get("codigo") or item.get("sku"))
        quantidade = int(float(item.get("quantidade") or 0))
        if not sku or quantidade <= 0:
            continue

        item_pedido = PedidoIntegradoItem(
            tenant_id=pedido.tenant_id,
            pedido_integrado_id=pedido.id,
            sku=sku,
            descricao=_text(item.get("descricao")),
            quantidade=quantidade,
        )
        try:
            EstoqueReservaService.reservar(db, item_pedido)
        except ValueError:
            pass
        db.add(item_pedido)
        itens_criados += 1

    return itens_criados > 0, {"itens_criados": itens_criados}


def _liberar_reservas_pedido_finalizado(db: Session, pedido: PedidoIntegrado, itens: list[PedidoIntegradoItem]) -> tuple[bool, dict]:
    liberados = 0
    agora = _utcnow()
    for item in itens:
        if item.liberado_em or item.vendido_em:
            continue
        item.liberado_em = agora
        db.add(item)
        liberados += 1
    return liberados > 0, {"itens_liberados": liberados}


def _reconciliar_pedido_confirmado(db: Session, pedido: PedidoIntegrado, itens: list[PedidoIntegradoItem]) -> tuple[bool, dict]:
    from app.services.bling_nf_service import processar_nf_autorizada

    nf = _ultima_nf(getattr(pedido, "payload", None))
    nf_id = _nf_bling_id_valido(_primeiro_preenchido(nf.get("id"), nf.get("nfe_id")))
    if not _nf_contexto_autorizado(nf) or not nf_id:
        nf_cache = None
        motivo_cache = "nf_ausente_ou_nao_autorizada"

        pedido_bling_id = _text(getattr(pedido, "pedido_bling_id", None))
        if pedido_bling_id:
            nf_cache = (
                db.query(BlingNotaFiscalCache)
                .filter(
                    BlingNotaFiscalCache.tenant_id == pedido.tenant_id,
                    BlingNotaFiscalCache.pedido_bling_id_ref == pedido_bling_id,
                )
                .order_by(
                    BlingNotaFiscalCache.data_emissao.desc().nullslast(),
                    BlingNotaFiscalCache.last_synced_at.desc().nullslast(),
                    BlingNotaFiscalCache.id.desc(),
                )
                .first()
            )
            if nf_cache and not _nf_contexto_autorizado({"situacao": getattr(nf_cache, "status", None)}):
                nf_cache = None

        if not nf_cache:
            numero_pedido_loja = _numero_pedido_loja_pedido(pedido)
            loja_id_pedido = _loja_id_pedido_integrado(pedido)
            if numero_pedido_loja:
                notas_loja = (
                    db.query(BlingNotaFiscalCache)
                    .filter(
                        BlingNotaFiscalCache.tenant_id == pedido.tenant_id,
                        BlingNotaFiscalCache.numero_pedido_loja == numero_pedido_loja,
                    )
                    .order_by(
                        BlingNotaFiscalCache.data_emissao.desc().nullslast(),
                        BlingNotaFiscalCache.last_synced_at.desc().nullslast(),
                        BlingNotaFiscalCache.id.desc(),
                    )
                    .all()
                )
                notas_loja = [
                    nota
                    for nota in notas_loja
                    if _nf_contexto_autorizado({"situacao": getattr(nota, "status", None)})
                ]
                if loja_id_pedido:
                    notas_loja = [
                        nota
                        for nota in notas_loja
                        if not _loja_id_nf_contexto(
                            _dict(getattr(nota, "detalhe_payload", None)) or _dict(getattr(nota, "resumo_payload", None))
                        )
                        or _loja_id_nf_contexto(
                            _dict(getattr(nota, "detalhe_payload", None)) or _dict(getattr(nota, "resumo_payload", None))
                        ) == loja_id_pedido
                    ]
                notas_unicas: dict[str, BlingNotaFiscalCache] = {}
                for nota in notas_loja:
                    pedido_ref_nota = _text(getattr(nota, "pedido_bling_id_ref", None))
                    if pedido_ref_nota and pedido_ref_nota != _text(getattr(pedido, "pedido_bling_id", None)):
                        continue
                    chave = _nf_bling_id_valido(getattr(nota, "bling_id", None)) or _text(getattr(nota, "numero", None)) or ""
                    if chave and chave not in notas_unicas:
                        notas_unicas[chave] = nota
                if len(notas_unicas) == 1:
                    nf_cache = next(iter(notas_unicas.values()))
                elif len(notas_unicas) > 1:
                    motivo_cache = "nf_cache_ambigua_por_numero_pedido_loja"
                else:
                    motivo_cache = "nf_cache_nao_encontrada"

        if not nf_cache:
            return False, {
                "motivo": motivo_cache,
                "nf_id": nf_id,
            }

        from app.integracao_bling_nf_routes import _registrar_nf_no_pedido

        detalhe_nf = _dict(getattr(nf_cache, "detalhe_payload", None))
        resumo_nf = _dict(getattr(nf_cache, "resumo_payload", None))
        dados_nf = detalhe_nf or resumo_nf or {}
        _registrar_nf_no_pedido(
            pedido=pedido,
            data=dados_nf,
            nf_id=_nf_bling_id_valido(getattr(nf_cache, "bling_id", None)) or "",
            situacao_num=5,
        )
        db.add(pedido)
        db.flush()

        nf = _ultima_nf(getattr(pedido, "payload", None))
        nf_id = _nf_bling_id_valido(_primeiro_preenchido(nf.get("id"), nf.get("nfe_id")))
        if not _nf_contexto_autorizado(nf) or not nf_id:
            return False, {
                "motivo": "nf_cache_nao_consolidada_no_pedido",
                "nf_id": nf_id,
            }

    acao = processar_nf_autorizada(
        db=db,
        pedido=pedido,
        itens=itens,
        nf_id=nf_id,
    )
    return acao in {"venda_confirmada", "venda_ja_confirmada"}, {
        "acao": acao,
        "nf_id": nf_id,
    }


def autocorrigir_incidente(db: Session, incidente: BlingFlowIncident) -> dict:
    from app.services.bling_nf_service import criar_produto_automatico_do_bling

    pedido = None
    if incidente.pedido_integrado_id:
        pedido = db.query(PedidoIntegrado).filter(
            PedidoIntegrado.id == incidente.pedido_integrado_id,
            PedidoIntegrado.tenant_id == incidente.tenant_id,
        ).first()
    if not pedido and incidente.pedido_bling_id:
        pedido = db.query(PedidoIntegrado).filter(
            PedidoIntegrado.pedido_bling_id == incidente.pedido_bling_id,
            PedidoIntegrado.tenant_id == incidente.tenant_id,
        ).first()

    try:
        if incidente.code == "SKU_SEM_PRODUTO_LOCAL":
            produto = criar_produto_automatico_do_bling(
                db=db,
                tenant_id=incidente.tenant_id,
                sku=incidente.sku or "",
            )
            sucesso = produto is not None
            detalhes = {"produto_id": getattr(produto, "id", None)}
        elif pedido and incidente.code == "PEDIDO_SEM_ITENS":
            sucesso, detalhes = _recarregar_itens_do_pedido(db, pedido)
        elif pedido and incidente.code == "RESERVA_ATIVA_EM_PEDIDO_FINALIZADO":
            itens = db.query(PedidoIntegradoItem).filter(
                PedidoIntegradoItem.pedido_integrado_id == pedido.id
            ).all()
            sucesso, detalhes = _liberar_reservas_pedido_finalizado(db, pedido, itens)
        elif pedido and incidente.code in {
            "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
            "NF_AUTORIZADA_PEDIDO_NAO_CONFIRMADO",
            "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
        }:
            itens = db.query(PedidoIntegradoItem).filter(
                PedidoIntegradoItem.pedido_integrado_id == pedido.id
            ).all()
            sucesso, detalhes = _reconciliar_pedido_confirmado(db, pedido, itens)
        elif pedido and incidente.code == "NF_ENCONTRADA_SEM_VINCULO_NO_PEDIDO":
            sucesso, detalhes = _vincular_nf_detectada_ao_pedido(
                db,
                pedido,
                _dict(_dict(incidente.details).get("nf_detectada")),
            )
        else:
            sucesso = False
            detalhes = {"motivo": "autofix_nao_implementado"}

        incidente.auto_fix_status = "applied" if sucesso else "failed"
        detalhes_atuais = _dict(incidente.details)
        detalhes_atuais["auto_fix_result"] = _json_safe(detalhes)
        incidente.details = detalhes_atuais
        if sucesso:
            incidente.status = "resolved"
            incidente.resolved_em = _utcnow()
        db.add(incidente)
        db.commit()
        db.refresh(incidente)

        registrar_evento(
            tenant_id=incidente.tenant_id,
            source="autofix",
            event_type=f"incident.{incidente.code}",
            entity_type="incidente",
            status="ok" if sucesso else "error",
            severity="info" if sucesso else "high",
            message="Autocorrecao executada" if sucesso else "Autocorrecao falhou",
            error_message=None if sucesso else str(detalhes),
            pedido_integrado_id=incidente.pedido_integrado_id,
            pedido_bling_id=incidente.pedido_bling_id,
            nf_bling_id=incidente.nf_bling_id,
            sku=incidente.sku,
            payload={"incident_id": incidente.id, "result": _json_safe(detalhes)},
            auto_fix_applied=sucesso,
        )

        return {
            "success": sucesso,
            "incident_id": incidente.id,
            "details": _json_safe(detalhes),
        }
    except Exception as exc:
        db.rollback()
        incidente.auto_fix_status = "failed"
        detalhes_atuais = _dict(incidente.details)
        detalhes_atuais["auto_fix_error"] = str(exc)
        incidente.details = detalhes_atuais
        db.add(incidente)
        db.commit()

        registrar_evento(
            tenant_id=incidente.tenant_id,
            source="autofix",
            event_type=f"incident.{incidente.code}",
            entity_type="incidente",
            status="error",
            severity="critical",
            message="Autocorrecao falhou com excecao",
            error_message=str(exc),
            pedido_integrado_id=incidente.pedido_integrado_id,
            pedido_bling_id=incidente.pedido_bling_id,
            nf_bling_id=incidente.nf_bling_id,
            sku=incidente.sku,
            payload={"incident_id": incidente.id},
            auto_fix_applied=False,
        )
        return {
            "success": False,
            "incident_id": incidente.id,
            "details": {"error": str(exc)},
        }


def auditar_fluxo_bling(
    db: Session,
    *,
    tenant_id=None,
    dias: int = 7,
    limite: int = 300,
    auto_fix: bool = True,
) -> dict:
    _garantir_registry_sqlalchemy_auditoria()
    cutoff = _utcnow() - timedelta(days=max(1, dias))
    query = db.query(PedidoIntegrado).filter(PedidoIntegrado.criado_em >= cutoff)
    if tenant_id:
        query = query.filter(PedidoIntegrado.tenant_id == tenant_id)

    pedidos = (
        query.order_by(PedidoIntegrado.criado_em.desc(), PedidoIntegrado.id.desc())
        .limit(max(1, min(limite, 1000)))
        .all()
    )

    incidentes_detectados = 0
    incidentes_resolvidos = 0
    auto_fix_tentados = 0
    auto_fix_sucessos = 0
    nfs_recentes_por_tenant: dict[Any, dict[str, list[dict]]] = {}

    for pedido in pedidos:
        try:
            itens = db.query(PedidoIntegradoItem).filter(
                PedidoIntegradoItem.pedido_integrado_id == pedido.id
            ).all()
            movimentacoes_saida, movimentacoes_saida_nf = _contar_movimentacoes_saida_nf(
                db,
                pedido,
                payload=_dict(pedido.payload),
            )

            itens_sem_produto = []
            itens_mapeados_por_barra = []
            for item in itens:
                produto, modo = _produto_por_sku(db, pedido.tenant_id, item.sku)
                if not produto:
                    itens_sem_produto.append(
                        {
                            "sku": item.sku,
                            "descricao": item.descricao,
                            "quantidade": item.quantidade,
                        }
                    )
                elif modo == "codigo_barras":
                    itens_mapeados_por_barra.append(
                        {
                            "sku": item.sku,
                            "produto_id": produto.id,
                            "produto_codigo": produto.codigo,
                            "produto_codigo_barras": produto.codigo_barras,
                        }
                    )

            nfs_detectadas: list[dict] = []
            numero_pedido_loja = _numero_pedido_loja_pedido(pedido)
            precisa_auditar_nfs_recentes = bool(
                numero_pedido_loja
                and (
                    pedido.status in {"aberto", "expirado", "confirmado"}
                )
            )
            if precisa_auditar_nfs_recentes:
                if pedido.tenant_id not in nfs_recentes_por_tenant:
                    try:
                        notas_recentes = _obter_nfs_recentes_bling(
                            tenant_id=pedido.tenant_id,
                            dias=max(1, min(dias, 5)),
                            db=db,
                        )
                        nfs_recentes_por_tenant[pedido.tenant_id] = _indexar_nfs_por_pedido_loja(notas_recentes)
                    except Exception as exc:
                        nfs_recentes_por_tenant[pedido.tenant_id] = {}
                        registrar_evento(
                            tenant_id=pedido.tenant_id,
                            source="auditoria",
                            event_type="invoice.lookup.failed",
                            entity_type="nf",
                            status="error",
                            severity="medium",
                            message="Falha ao consultar NFs recentes no Bling durante a auditoria",
                            error_message=str(exc),
                            pedido_integrado_id=pedido.id,
                            pedido_bling_id=pedido.pedido_bling_id,
                            payload={"numero_pedido_loja": numero_pedido_loja},
                            db=db,
                        )
                nfs_detectadas = nfs_recentes_por_tenant.get(pedido.tenant_id, {}).get(numero_pedido_loja, [])

            incidentes = diagnosticar_pedido_integrado(
                pedido,
                itens,
                _dict(pedido.payload),
                movimentacoes_saida=movimentacoes_saida,
                movimentacoes_saida_nf=movimentacoes_saida_nf,
                itens_sem_produto=itens_sem_produto,
                itens_mapeados_por_barra=itens_mapeados_por_barra,
                nf_detectada=nfs_detectadas[0] if len(nfs_detectadas) == 1 else None,
                nfs_detectadas=nfs_detectadas,
            )
            active_keys: set[str] = set()

            for incidente_data in incidentes:
                incidentes_detectados += 1
                incidente = abrir_incidente(
                    tenant_id=pedido.tenant_id,
                    code=incidente_data["code"],
                    severity=incidente_data["severity"],
                    title=incidente_data["title"],
                    message=incidente_data["message"],
                    suggested_action=incidente_data["suggested_action"],
                    auto_fixable=incidente_data["auto_fixable"],
                    pedido_integrado_id=incidente_data["pedido_integrado_id"],
                    pedido_bling_id=incidente_data["pedido_bling_id"],
                    nf_bling_id=incidente_data["nf_bling_id"],
                    sku=incidente_data["sku"],
                    details=incidente_data["details"],
                    source="auditoria",
                    db=db,
                )
                if not incidente:
                    continue
                active_keys.add(incidente.dedupe_key)

                if auto_fix and incidente.auto_fixable and incidente.status == "open":
                    auto_fix_tentados += 1
                    resultado = autocorrigir_incidente(db, incidente)
                    if resultado.get("success"):
                        auto_fix_sucessos += 1

            incidentes_resolvidos += _resolver_incidentes_ausentes(db, pedido, active_keys)
            db.commit()
        except Exception as exc:
            db.rollback()
            registrar_evento(
                tenant_id=pedido.tenant_id,
                source="auditoria",
                event_type="pedido.audit",
                entity_type="pedido",
                status="error",
                severity="high",
                message="Falha ao auditar pedido integrado",
                error_message=str(exc),
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido.pedido_bling_id,
            )

    incidentes_abertos_query = db.query(BlingFlowIncident).filter(
        BlingFlowIncident.status == "open",
        BlingFlowIncident.code.in_(list(MONITORED_INCIDENT_CODES)),
    )
    if tenant_id:
        incidentes_abertos_query = incidentes_abertos_query.filter(
            BlingFlowIncident.tenant_id == tenant_id
        )

    return {
        "pedidos_auditados": len(pedidos),
        "incidentes_detectados": incidentes_detectados,
        "incidentes_resolvidos": incidentes_resolvidos,
        "auto_fix_tentados": auto_fix_tentados,
        "auto_fix_sucessos": auto_fix_sucessos,
        "incidentes_abertos": incidentes_abertos_query.count(),
        "cutoff": cutoff.isoformat(),
    }


def obter_resumo_monitoramento(db: Session, *, tenant_id=None) -> dict:
    incidentes_query = db.query(BlingFlowIncident).filter(BlingFlowIncident.status == "open")
    eventos_query = db.query(BlingFlowEvent)
    if tenant_id:
        incidentes_query = incidentes_query.filter(BlingFlowIncident.tenant_id == tenant_id)
        eventos_query = eventos_query.filter(BlingFlowEvent.tenant_id == tenant_id)

    incidentes_abertos = incidentes_query.all()
    eventos_recentes = eventos_query.order_by(
        BlingFlowEvent.processed_at.desc(),
        BlingFlowEvent.id.desc(),
    ).limit(10).all()

    por_severidade = Counter(inc.severity for inc in incidentes_abertos)
    por_codigo = Counter(inc.code for inc in incidentes_abertos)

    return {
        "status": "critical" if por_severidade.get("critical") else ("warning" if incidentes_abertos else "healthy"),
        "incidentes_abertos": len(incidentes_abertos),
        "por_severidade": dict(por_severidade),
        "por_codigo": dict(por_codigo),
        "eventos_recentes": [
            {
                "id": evento.id,
                "event_type": evento.event_type,
                "status": evento.status,
                "severity": evento.severity,
                "message": evento.message,
                "pedido_bling_id": evento.pedido_bling_id,
                "nf_bling_id": evento.nf_bling_id,
                "sku": evento.sku,
                "processed_at": serializar_data_evento_monitor(evento.processed_at),
            }
            for evento in eventos_recentes
        ],
    }


def executar_auditoria_background(*, dias: int = 7, limite: int = 300, auto_fix: bool = True) -> dict:
    db = SessionLocal()
    try:
        resultado = auditar_fluxo_bling(db, dias=dias, limite=limite, auto_fix=auto_fix)
        logger.info(
            "[BLING FLOW MONITOR] Auditoria concluida: "
            f"pedidos={resultado['pedidos_auditados']} "
            f"incidentes={resultado['incidentes_detectados']} "
            f"autofix={resultado['auto_fix_sucessos']}/{resultado['auto_fix_tentados']}"
        )
        return resultado
    finally:
        db.close()
