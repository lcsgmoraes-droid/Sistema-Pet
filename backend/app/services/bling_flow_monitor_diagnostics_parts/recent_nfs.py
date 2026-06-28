from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from time import monotonic, sleep

from sqlalchemy.orm import Session

from app.nfe_cache_models import BlingNotaFiscalCache
from app.pedido_integrado_models import PedidoIntegrado
from app.services.bling_flow_monitor_diagnostics_parts.context import (
    _canal_label_nf_contexto,
    _canal_pedido_integrado,
    _loja_id_nf_contexto,
    _loja_id_pedido_integrado,
    _nf_contexto_autorizado,
    _numero_pedido_loja_pedido,
    _pedido_total,
)
from app.services.bling_flow_monitor_utils import (
    _coerce_int,
    _dict,
    _list,
    _primeiro_preenchido,
    _text,
    _utcnow,
)
from app.utils.logger import logger


_NF_RECENTES_CACHE_SECONDS = 300
_NF_RECENTES_ENRICH_LIMIT = 60
_NF_RECENTES_ENRICH_DELAY_SECONDS = 0.35
_nf_recentes_cache: dict[tuple[str, int], dict] = {}


def _resumir_nf_bling_recente(item: dict, modelo: int) -> dict:
    item = _dict(item)
    try:
        from app.integracao_bling_nf_routes import _extrair_numero_pedido_loja_nf
    except Exception:
        numero_pedido_loja = None
    else:
        numero_pedido_loja = _extrair_numero_pedido_loja_nf(item)

    pedido_ref = _dict(
        item.get("pedido") or item.get("pedidoVenda") or item.get("pedidoCompra")
    )
    canal, canal_label = _canal_label_nf_contexto(item)

    return {
        "id": _text(item.get("id")),
        "numero": _text(item.get("numero")),
        "serie": _text(item.get("serie")),
        "modelo": modelo,
        "situacao_codigo": _coerce_int(item.get("situacao"), 0),
        "situacao": _text(item.get("descricaoSituacao") or item.get("situacao")),
        "chave": _text(item.get("chaveAcesso") or item.get("chave")),
        "valor_total": item.get("valorNota")
        or item.get("valorTotalNf")
        or item.get("valorTotal")
        or item.get("valor_total"),
        "data_emissao": _text(
            item.get("dataEmissao") or item.get("data_emissao") or item.get("data")
        ),
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
        logger.warning(
            f"[BLING FLOW MONITOR] Falha ao enriquecer NF recente {nf_id}: {exc}"
        )
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
        "pedido_bling_id": _text(relacao.get("pedido_bling_id"))
        or _text(resumo.get("pedido_bling_id")),
        "pedido_bling_numero": _text(relacao.get("pedido_bling_numero"))
        or _text(resumo.get("pedido_bling_numero")),
        "numero_pedido_loja": _text(relacao.get("numero_pedido_loja"))
        or _text(resumo.get("numero_pedido_loja")),
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
        .order_by(
            BlingNotaFiscalCache.data_emissao.desc(), BlingNotaFiscalCache.id.desc()
        )
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
            "situacao_codigo": 5
            if (_text(getattr(registro, "status", None)) or "").lower() == "autorizada"
            else 0,
            "chave": _text(getattr(registro, "chave", None)),
            "valor_total": getattr(registro, "valor", None),
            "data_emissao": getattr(registro, "data_emissao", None).isoformat()
            if getattr(registro, "data_emissao", None)
            else None,
            "numero_pedido_loja": _text(getattr(registro, "numero_pedido_loja", None)),
            "loja_id": _loja_id_nf_contexto(
                _dict(getattr(registro, "detalhe_payload", None))
                or _dict(getattr(registro, "resumo_payload", None))
            ),
            "pedido_bling_id": _text(getattr(registro, "pedido_bling_id_ref", None)),
            "pedido_bling_numero": _text(
                _dict(getattr(registro, "detalhe_payload", None)).get(
                    "pedido_bling_numero"
                )
            )
            or _text(
                _dict(getattr(registro, "resumo_payload", None)).get(
                    "pedido_bling_numero"
                )
            ),
            "canal": _text(getattr(registro, "canal", None)),
            "canal_label": _text(getattr(registro, "canal_label", None)),
        }
        if resumo.get("numero_pedido_loja") or resumo.get("pedido_bling_numero"):
            notas.append(resumo)
    return notas


def _obter_nfs_recentes_bling(
    *, tenant_id, dias: int, db: Session | None = None
) -> list[dict]:
    dias = max(1, min(int(dias or 1), 15))
    cache_key = (str(tenant_id or ""), dias)
    cache_atual = _nf_recentes_cache.get(cache_key)
    if (
        cache_atual
        and (monotonic() - cache_atual.get("ts_monotonic", 0))
        <= _NF_RECENTES_CACHE_SECONDS
    ):
        return deepcopy(cache_atual.get("items") or [])

    notas_cache_local = (
        _obter_nfs_recentes_cache_local(db, tenant_id=tenant_id, dias=dias)
        if db
        else []
    )
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
            logger.warning(
                f"[BLING FLOW MONITOR] Falha ao listar notas recentes do Bling (modelo {modelo}): {exc}"
            )
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
        if not any(
            _text(item.get("id")) == _text(_dict(nf).get("id")) for item in mapa[numero]
        ):
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


def _nf_detectada_combina_com_pedido(
    pedido: PedidoIntegrado, nf_contexto: dict | None
) -> tuple[bool, dict]:
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
