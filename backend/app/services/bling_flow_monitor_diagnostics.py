from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from time import monotonic, sleep

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.nfe_cache_models import BlingNotaFiscalCache
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao, Produto
from app.services.bling_flow_monitor_utils import (
    _coerce_int,
    _dict,
    _json_safe,
    _list,
    _nf_bling_id_valido,
    _normalizar_contexto_nf,
    _primeiro_preenchido,
    _text,
    _utcnow,
)
from app.utils.logger import logger


NF_AUTHORIZED_CODES = {2, 5, 9}
_NF_RECENTES_CACHE_SECONDS = 300
_NF_RECENTES_ENRICH_LIMIT = 60
_NF_RECENTES_ENRICH_DELAY_SECONDS = 0.35
_nf_recentes_cache: dict[tuple[str, int], dict] = {}


def _ultima_nf(payload: dict | None) -> dict:
    payload = _dict(payload)
    pedido = _dict(payload.get("pedido"))
    for candidato in (
        payload.get("ultima_nf"),
        pedido.get("notaFiscal"),
        pedido.get("nota"),
        pedido.get("nfe"),
    ):
        nf = _normalizar_contexto_nf(candidato)
        if nf:
            return nf
    return {}


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


def _produto_por_sku(
    db: Session, tenant_id, sku: str
) -> tuple[Produto | None, str | None]:
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
    nfs_detectadas = [
        _dict(item) for item in (nfs_detectadas or []) if isinstance(item, dict)
    ]
    nf_auditavel = nf
    if (
        not _nf_contexto_autorizado(nf)
        and len(nfs_detectadas) == 1
        and _nf_contexto_autorizado(nfs_detectadas[0])
    ):
        nf_auditavel = nfs_detectadas[0]
    nf_local_id = _text(nf.get("id"))
    nf_local_numero = _text(nf.get("numero"))
    movimentacoes_saida_nf = (
        movimentacoes_saida
        if movimentacoes_saida_nf is None
        else int(movimentacoes_saida_nf)
    )

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
                        nf_bling_id=_text(
                            _primeiro_preenchido(nf_auditavel.get("id"), nf.get("id"))
                        ),
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
                    nf_bling_id=_text(
                        _primeiro_preenchido(nf_auditavel.get("id"), nf.get("id"))
                    ),
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
            if not getattr(item, "liberado_em", None) and not getattr(
                item, "vendido_em", None
            ):
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
                or (
                    nf_local_numero
                    and nf_detectada_numero
                    and nf_local_numero == nf_detectada_numero
                )
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
                                "numero_pedido_loja": _numero_pedido_loja_pedido(
                                    pedido
                                ),
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
