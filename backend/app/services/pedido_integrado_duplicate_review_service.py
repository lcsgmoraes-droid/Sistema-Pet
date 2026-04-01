from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import EstoqueMovimentacao
from app.services.pedido_integrado_consolidation_service import (
    escolher_pedido_canonico,
    listar_pedidos_por_numero_loja,
    loja_id_do_payload,
    numero_pedido_loja_do_payload,
    pedido_tem_nf_deterministica,
    registrar_alias_bling_no_payload,
    resolver_pedido_canonico,
    ultima_nf_do_payload,
)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _dt_iso(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return _text(value)


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _utcnow() -> datetime:
    return datetime.utcnow()


def _item_key(item: PedidoIntegradoItem | dict | None) -> tuple[str | None, int]:
    item_dict = _dict(item)
    sku = _text(getattr(item, "sku", None) if item is not None else item_dict.get("sku"))
    quantidade = _coerce_int(
        getattr(item, "quantidade", None) if item is not None else item_dict.get("quantidade"),
        0,
    )
    return sku, quantidade


def _numero_nf_pedido(pedido: PedidoIntegrado) -> str | None:
    ultima_nf = ultima_nf_do_payload(pedido)
    return _text(ultima_nf.get("numero"))


def _nf_bling_id_pedido(pedido: PedidoIntegrado) -> str | None:
    ultima_nf = ultima_nf_do_payload(pedido)
    return _text(ultima_nf.get("id") or ultima_nf.get("nfe_id"))


def _resumo_item(item: PedidoIntegradoItem) -> dict:
    if getattr(item, "vendido_em", None):
        situacao = "vendido"
    elif getattr(item, "liberado_em", None):
        situacao = "liberado"
    else:
        situacao = "reservado"
    return {
        "id": getattr(item, "id", None),
        "sku": _text(getattr(item, "sku", None)),
        "quantidade": _coerce_int(getattr(item, "quantidade", None), 0),
        "situacao": situacao,
        "reservado_em": _dt_iso(getattr(item, "reservado_em", None)),
        "liberado_em": _dt_iso(getattr(item, "liberado_em", None)),
        "vendido_em": _dt_iso(getattr(item, "vendido_em", None)),
    }


def _resumo_movimentacao(mov: EstoqueMovimentacao) -> dict:
    return {
        "id": getattr(mov, "id", None),
        "tipo": _text(getattr(mov, "tipo", None)),
        "status": _text(getattr(mov, "status", None)),
        "produto_id": getattr(mov, "produto_id", None),
        "quantidade": float(getattr(mov, "quantidade", 0) or 0),
        "documento": _text(getattr(mov, "documento", None)),
    }


def _agrupar_itens_por_pedido(db: Session, pedido_ids: list[int]) -> dict[int, list[PedidoIntegradoItem]]:
    if not pedido_ids:
        return {}
    itens = (
        db.query(PedidoIntegradoItem)
        .filter(PedidoIntegradoItem.pedido_integrado_id.in_(pedido_ids))
        .order_by(PedidoIntegradoItem.id.asc())
        .all()
    )
    agrupados: dict[int, list[PedidoIntegradoItem]] = defaultdict(list)
    for item in itens:
        agrupados[int(item.pedido_integrado_id)].append(item)
    return dict(agrupados)


def _agrupar_movimentos_por_pedido(db: Session, tenant_id, pedido_ids: list[int]) -> dict[int, list[EstoqueMovimentacao]]:
    if not pedido_ids:
        return {}
    movimentos = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.referencia_id.in_(pedido_ids),
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )
    agrupados: dict[int, list[EstoqueMovimentacao]] = defaultdict(list)
    for mov in movimentos:
        agrupados[int(mov.referencia_id)].append(mov)
    return dict(agrupados)


def _resumir_pedido(
    pedido: PedidoIntegrado,
    *,
    itens: list[PedidoIntegradoItem],
    movimentos: list[EstoqueMovimentacao],
    canonical_item_counter: Counter | None = None,
    canonical_nf_key: tuple[str | None, str | None] | None = None,
) -> dict:
    numero_pedido_loja = numero_pedido_loja_do_payload(pedido)
    loja_id = loja_id_do_payload(pedido)
    nf_numero = _numero_nf_pedido(pedido)
    nf_bling_id = _nf_bling_id_pedido(pedido)
    movimentos_ativos = [mov for mov in movimentos if _text(getattr(mov, "status", None)) != "cancelado"]
    itens_vendidos = [item for item in itens if getattr(item, "vendido_em", None)]
    itens_liberados = [item for item in itens if getattr(item, "liberado_em", None)]
    itens_reservados = [
        item
        for item in itens
        if not getattr(item, "vendido_em", None) and not getattr(item, "liberado_em", None)
    ]

    motivos: list[str] = []
    recomendacao = "mesclar_payload"
    if itens_vendidos:
        motivos.append("possui_item_vendido")
    if movimentos_ativos:
        motivos.append("possui_movimentacao_estoque")

    nf_key = (_text(nf_bling_id), _text(nf_numero))
    if canonical_nf_key and pedido_tem_nf_deterministica(pedido):
        canonical_nf_id, canonical_nf_numero = canonical_nf_key
        if canonical_nf_id or canonical_nf_numero:
            if canonical_nf_id and nf_key[0] and canonical_nf_id != nf_key[0]:
                motivos.append("nf_deterministica_divergente")
            elif canonical_nf_numero and nf_key[1] and canonical_nf_numero != nf_key[1]:
                motivos.append("nf_deterministica_divergente")

    if not motivos and itens_reservados and canonical_item_counter:
        contador_reservas_duplicado = Counter(_item_key(item) for item in itens_reservados)
        if all(canonical_item_counter.get(chave, 0) >= quantidade for chave, quantidade in contador_reservas_duplicado.items()):
            recomendacao = "liberar_itens_redundantes"
        else:
            recomendacao = "transferir_itens_para_canonico"

    return {
        "id": pedido.id,
        "pedido_bling_id": _text(getattr(pedido, "pedido_bling_id", None)),
        "pedido_bling_numero": _text(getattr(pedido, "pedido_bling_numero", None)),
        "status": _text(getattr(pedido, "status", None)),
        "canal": _text(getattr(pedido, "canal", None)),
        "numero_pedido_loja": numero_pedido_loja,
        "loja_id": loja_id,
        "nf_numero": nf_numero,
        "nf_bling_id": nf_bling_id,
        "criado_em": _dt_iso(getattr(pedido, "criado_em", None)),
        "confirmado_em": _dt_iso(getattr(pedido, "confirmado_em", None)),
        "cancelado_em": _dt_iso(getattr(pedido, "cancelado_em", None)),
        "tem_nf_deterministica": pedido_tem_nf_deterministica(pedido),
        "itens_total": len(itens),
        "itens_reservados": len(itens_reservados),
        "itens_liberados": len(itens_liberados),
        "itens_vendidos": len(itens_vendidos),
        "movimentos_total": len(movimentos),
        "movimentos_ativos": len(movimentos_ativos),
        "pode_mesclar_automaticamente": not motivos,
        "motivos_bloqueio": motivos,
        "acao_recomendada": recomendacao,
        "itens": [_resumo_item(item) for item in itens],
        "movimentos": [_resumo_movimentacao(mov) for mov in movimentos_ativos[:10]],
    }


def _mesclar_payloads_pedido(canonico: PedidoIntegrado, duplicado: PedidoIntegrado, *, merged_at: datetime) -> None:
    from app.integracao_bling_pedido_routes import _consolidar_ultima_nf

    payload_canonico = dict(_dict(getattr(canonico, "payload", None)))
    payload_duplicado = _dict(getattr(duplicado, "payload", None))
    numero_pedido_loja = numero_pedido_loja_do_payload(duplicado)
    loja_id = loja_id_do_payload(duplicado)

    payload_canonico = registrar_alias_bling_no_payload(
        payload_canonico,
        pedido_bling_id=_text(getattr(duplicado, "pedido_bling_id", None)),
        pedido_bling_numero=_text(getattr(duplicado, "pedido_bling_numero", None)),
        numero_pedido_loja=numero_pedido_loja,
        loja_id=loja_id,
        merged_at=merged_at,
        motivo="numero_pedido_loja_duplicado",
    )

    ultima_nf_duplicado = ultima_nf_do_payload(duplicado)
    if ultima_nf_duplicado:
        payload_canonico["ultima_nf"] = _consolidar_ultima_nf(
            payload_canonico.get("ultima_nf"),
            ultima_nf_duplicado,
        )

    pedido_canonico_payload = _dict(payload_canonico.get("pedido"))
    pedido_duplicado_payload = _dict(payload_duplicado.get("pedido"))
    if pedido_duplicado_payload:
        if not pedido_canonico_payload.get("itens") and pedido_duplicado_payload.get("itens"):
            pedido_canonico_payload["itens"] = pedido_duplicado_payload.get("itens")
        for chave in ("numeroPedidoLoja", "numeroLoja", "numeroPedidoCanalVenda", "numeroPedidoCanal", "numeroPedidoMarketplace"):
            if not pedido_canonico_payload.get(chave) and pedido_duplicado_payload.get(chave):
                pedido_canonico_payload[chave] = pedido_duplicado_payload.get(chave)
        payload_canonico["pedido"] = pedido_canonico_payload or pedido_duplicado_payload

    canonico.payload = payload_canonico


def listar_grupos_duplicados_pedido_loja(
    db: Session,
    *,
    tenant_id,
    pedido_ids: list[int] | None = None,
    dias: int | None = None,
    limite_scan: int = 4000,
) -> list[dict]:
    query = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.tenant_id == tenant_id,
        PedidoIntegrado.status != "mesclado",
    )
    if dias:
        cutoff = _utcnow() - timedelta(days=max(int(dias), 1))
        query = query.filter(PedidoIntegrado.criado_em >= cutoff)

    pedidos = (
        query.order_by(PedidoIntegrado.criado_em.desc(), PedidoIntegrado.id.desc())
        .limit(max(int(limite_scan or 0), 1))
        .all()
    )
    if not pedidos:
        return []

    pedido_ids_set = {int(pedido_id) for pedido_id in (pedido_ids or []) if pedido_id}
    grupos: dict[tuple[str, str], list[PedidoIntegrado]] = defaultdict(list)
    for pedido in pedidos:
        numero = numero_pedido_loja_do_payload(pedido)
        if not numero:
            continue
        loja_id = loja_id_do_payload(pedido) or ""
        grupos[(numero, loja_id)].append(pedido)

    grupos_duplicados = [grupo for grupo in grupos.values() if len(grupo) > 1]
    if pedido_ids_set:
        grupos_duplicados = [
            grupo
            for grupo in grupos_duplicados
            if any(int(getattr(pedido, "id", 0) or 0) in pedido_ids_set for pedido in grupo)
        ]

    if not grupos_duplicados:
        return []

    ids = [int(pedido.id) for grupo in grupos_duplicados for pedido in grupo]
    itens_por_pedido = _agrupar_itens_por_pedido(db, ids)
    movimentos_por_pedido = _agrupar_movimentos_por_pedido(db, tenant_id, ids)

    resultados: list[dict] = []
    for grupo in grupos_duplicados:
        canonico = escolher_pedido_canonico(grupo)
        if not canonico:
            continue

        itens_canonico = itens_por_pedido.get(int(canonico.id), [])
        movimentos_canonico = movimentos_por_pedido.get(int(canonico.id), [])
        canonical_item_counter = Counter(_item_key(item) for item in itens_canonico if _item_key(item)[0])
        canonical_nf_key = (_nf_bling_id_pedido(canonico), _numero_nf_pedido(canonico))

        resumo_canonico = _resumir_pedido(
            canonico,
            itens=itens_canonico,
            movimentos=movimentos_canonico,
            canonical_item_counter=canonical_item_counter,
            canonical_nf_key=canonical_nf_key,
        )
        duplicados = []
        for pedido in grupo:
            if int(pedido.id) == int(canonico.id):
                continue
            duplicados.append(
                _resumir_pedido(
                    pedido,
                    itens=itens_por_pedido.get(int(pedido.id), []),
                    movimentos=movimentos_por_pedido.get(int(pedido.id), []),
                    canonical_item_counter=canonical_item_counter,
                    canonical_nf_key=canonical_nf_key,
                )
            )

        seguros = [item for item in duplicados if item.get("pode_mesclar_automaticamente")]
        bloqueados = [item for item in duplicados if not item.get("pode_mesclar_automaticamente")]
        resultados.append(
            {
                "numero_pedido_loja": resumo_canonico.get("numero_pedido_loja"),
                "loja_id": resumo_canonico.get("loja_id"),
                "pedido_canonico": resumo_canonico,
                "pedidos_duplicados": duplicados,
                "quantidade_duplicados": len(duplicados),
                "pode_consolidar_automaticamente": bool(seguros),
                "requer_revisao_manual": bool(bloqueados),
                "pedidos_seguro_ids": [item["id"] for item in seguros],
                "pedidos_bloqueados_ids": [item["id"] for item in bloqueados],
                "bloqueios": [
                    {
                        "pedido_id": item["id"],
                        "pedido_bling_numero": item.get("pedido_bling_numero"),
                        "motivos": item.get("motivos_bloqueio") or [],
                    }
                    for item in bloqueados
                ],
            }
        )

    resultados.sort(
        key=lambda item: (
            1 if item.get("pode_consolidar_automaticamente") else 0,
            _dt_iso(_dict(item.get("pedido_canonico")).get("criado_em")) or "",
            _coerce_int(_dict(item.get("pedido_canonico")).get("pedido_bling_numero"), 0),
        ),
        reverse=True,
    )
    return resultados


def mapear_duplicidade_por_pedido_ids(
    db: Session,
    *,
    tenant_id,
    pedido_ids: list[int],
    limite_scan: int = 4000,
) -> dict[int, dict]:
    grupos = listar_grupos_duplicados_pedido_loja(
        db,
        tenant_id=tenant_id,
        pedido_ids=pedido_ids,
        limite_scan=limite_scan,
    )
    mapa: dict[int, dict] = {}
    for grupo in grupos:
        pedido_canonico = _dict(grupo.get("pedido_canonico"))
        todos = [pedido_canonico, *(_dict(item) for item in grupo.get("pedidos_duplicados") or [])]
        for pedido in todos:
            pedido_id = _coerce_int(pedido.get("id"), 0)
            if pedido_id <= 0:
                continue
            mapa[pedido_id] = {
                "tem_duplicados": True,
                "numero_pedido_loja": grupo.get("numero_pedido_loja"),
                "loja_id": grupo.get("loja_id"),
                "pedido_canonico": pedido_canonico,
                "pedidos_duplicados": grupo.get("pedidos_duplicados") or [],
                "pode_consolidar_automaticamente": grupo.get("pode_consolidar_automaticamente", False),
                "requer_revisao_manual": grupo.get("requer_revisao_manual", False),
                "pedidos_seguro_ids": grupo.get("pedidos_seguro_ids") or [],
                "pedidos_bloqueados_ids": grupo.get("pedidos_bloqueados_ids") or [],
                "bloqueios": grupo.get("bloqueios") or [],
                "pedido_atual_eh_canonico": pedido_id == _coerce_int(pedido_canonico.get("id"), 0),
            }
    return mapa


def consolidar_duplicidades_seguras_pedido(
    db: Session,
    *,
    tenant_id,
    pedido_id: int,
) -> dict:
    pedido_base = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.id == pedido_id,
            PedidoIntegrado.tenant_id == tenant_id,
        )
        .first()
    )
    if not pedido_base:
        return {"success": False, "motivo": "pedido_nao_encontrado"}

    pedido_canonico = resolver_pedido_canonico(db, pedido_base) or pedido_base
    grupos = listar_grupos_duplicados_pedido_loja(
        db,
        tenant_id=tenant_id,
        pedido_ids=[int(getattr(pedido_canonico, "id", 0) or 0)],
    )
    if not grupos:
        return {"success": False, "motivo": "pedido_sem_duplicidade"}

    grupo = next(
        (
            item
            for item in grupos
            if _coerce_int(_dict(item.get("pedido_canonico")).get("id"), 0) == int(pedido_canonico.id)
        ),
        None,
    )
    if not grupo:
        return {"success": False, "motivo": "pedido_sem_duplicidade_canonica"}

    duplicados_seguro_ids = [int(item) for item in grupo.get("pedidos_seguro_ids") or [] if item]
    if not duplicados_seguro_ids:
        return {
            "success": False,
            "motivo": "duplicidades_requerem_revisao_manual",
            "grupo": grupo,
        }

    from app.integracao_bling_pedido_routes import _sincronizar_itens_pedido_integrado
    from app.services.bling_flow_monitor_service import registrar_evento, resolver_incidentes_relacionados
    from app.services.pedido_integrado_consolidation_service import marcar_payload_como_mesclado

    agora = _utcnow()
    itens_canonico = _agrupar_itens_por_pedido(db, [int(pedido_canonico.id)]).get(int(pedido_canonico.id), [])
    contador_canonico = Counter(_item_key(item) for item in itens_canonico if _item_key(item)[0])
    mesclados: list[dict] = []

    for duplicado_id in duplicados_seguro_ids:
        duplicado = (
            db.query(PedidoIntegrado)
            .filter(
                PedidoIntegrado.id == duplicado_id,
                PedidoIntegrado.tenant_id == tenant_id,
            )
            .first()
        )
        if not duplicado:
            continue

        itens_duplicado = _agrupar_itens_por_pedido(db, [duplicado_id]).get(duplicado_id, [])
        movimentos_duplicado = _agrupar_movimentos_por_pedido(db, tenant_id, [duplicado_id]).get(duplicado_id, [])
        if any(getattr(item, "vendido_em", None) for item in itens_duplicado):
            continue
        if any(_text(getattr(mov, "status", None)) != "cancelado" for mov in movimentos_duplicado):
            continue

        _mesclar_payloads_pedido(pedido_canonico, duplicado, merged_at=agora)
        if (not pedido_canonico.canal or pedido_canonico.canal == "bling") and duplicado.canal:
            pedido_canonico.canal = duplicado.canal
        if not pedido_canonico.pedido_bling_numero and duplicado.pedido_bling_numero:
            pedido_canonico.pedido_bling_numero = duplicado.pedido_bling_numero

        itens_movidos = 0
        itens_liberados = 0
        for item in itens_duplicado:
            chave = _item_key(item)
            if chave[0] is None:
                continue

            if getattr(item, "vendido_em", None):
                continue

            if not getattr(item, "liberado_em", None) and contador_canonico.get(chave, 0) > 0:
                item.liberado_em = item.liberado_em or agora
                contador_canonico[chave] = max(contador_canonico.get(chave, 0) - 1, 0)
                itens_liberados += 1
            else:
                item.pedido_integrado_id = pedido_canonico.id
                contador_canonico[chave] += 1
                itens_movidos += 1
            db.add(item)

        db.flush()
        itens_incorporados_payload = _sincronizar_itens_pedido_integrado(
            db,
            pedido=pedido_canonico,
            itens_bling=_dict(_dict(getattr(duplicado, "payload", None)).get("pedido")).get("itens") or [],
        )

        duplicado.payload = marcar_payload_como_mesclado(
            duplicado.payload,
            pedido_canonico=pedido_canonico,
            numero_pedido_loja=numero_pedido_loja_do_payload(duplicado),
            loja_id=loja_id_do_payload(duplicado),
            merged_at=agora,
            motivo="numero_pedido_loja_duplicado",
        )
        duplicado.status = "mesclado"
        duplicado.cancelado_em = duplicado.cancelado_em or agora
        db.add(duplicado)

        mesclados.append(
            {
                "pedido_id": duplicado.id,
                "pedido_bling_numero": _text(getattr(duplicado, "pedido_bling_numero", None)),
                "itens_movidos": itens_movidos,
                "itens_liberados": itens_liberados,
                "itens_incorporados_payload": itens_incorporados_payload,
            }
        )

    if not mesclados:
        return {
            "success": False,
            "motivo": "nenhuma_duplicidade_segura_aplicada",
            "grupo": grupo,
        }

    db.add(pedido_canonico)
    resolver_incidentes_relacionados(
        db,
        tenant_id=tenant_id,
        codes=["PEDIDO_DUPLICADO_POR_NUMERO_LOJA"],
        pedido_integrado_id=pedido_canonico.id,
        pedido_bling_id=pedido_canonico.pedido_bling_id,
        resolution_note="Duplicidades seguras consolidadas manualmente.",
    )
    db.commit()

    registrar_evento(
        tenant_id=tenant_id,
        source="manual",
        event_type="order.duplicate_consolidated",
        entity_type="pedido",
        status="ok",
        severity="warning",
        message="Pedidos duplicados foram consolidados no pedido canonico.",
        pedido_integrado_id=pedido_canonico.id,
        pedido_bling_id=pedido_canonico.pedido_bling_id,
        payload={
            "numero_pedido_loja": numero_pedido_loja_do_payload(pedido_canonico),
            "pedido_canonico_id": pedido_canonico.id,
            "pedidos_mesclados": mesclados,
        },
        db=db,
        auto_fix_applied=False,
    )

    return {
        "success": True,
        "pedido_canonico_id": pedido_canonico.id,
        "pedido_canonico_bling_numero": _text(getattr(pedido_canonico, "pedido_bling_numero", None)),
        "numero_pedido_loja": numero_pedido_loja_do_payload(pedido_canonico),
        "pedidos_mesclados": mesclados,
        "pedidos_bloqueados_ids": grupo.get("pedidos_bloqueados_ids") or [],
    }


def reconciliar_fluxo_pedido_integrado(
    db: Session,
    *,
    tenant_id,
    pedido_id: int,
) -> dict:
    from app.pedido_integrado_item_models import PedidoIntegradoItem
    from app.services.bling_flow_monitor_service import _reconciliar_pedido_confirmado, registrar_evento, resolver_incidentes_relacionados

    pedido_base = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.id == pedido_id,
            PedidoIntegrado.tenant_id == tenant_id,
        )
        .first()
    )
    if not pedido_base:
        return {"success": False, "motivo": "pedido_nao_encontrado"}

    pedido = resolver_pedido_canonico(db, pedido_base) or pedido_base
    consolidacao = consolidar_duplicidades_seguras_pedido(db, tenant_id=tenant_id, pedido_id=pedido.id)
    if consolidacao.get("success"):
        pedido = (
            db.query(PedidoIntegrado)
            .filter(
                PedidoIntegrado.id == pedido.id,
                PedidoIntegrado.tenant_id == tenant_id,
            )
            .first()
        ) or pedido

    itens = (
        db.query(PedidoIntegradoItem)
        .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
        .all()
    )
    if not itens:
        return {
            "success": False,
            "motivo": "pedido_sem_itens",
            "pedido_id": pedido.id,
            "consolidacao": consolidacao,
        }

    sucesso, detalhes = _reconciliar_pedido_confirmado(db, pedido, itens)
    if not sucesso:
        db.rollback()
        return {
            "success": False,
            "motivo": "reconciliacao_sem_sucesso",
            "pedido_id": pedido.id,
            "pedido_bling_numero": _text(getattr(pedido, "pedido_bling_numero", None)),
            "numero_pedido_loja": numero_pedido_loja_do_payload(pedido),
            "detalhes": detalhes,
            "consolidacao": consolidacao,
        }

    resolver_incidentes_relacionados(
        db,
        tenant_id=tenant_id,
        codes=[
            "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
            "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
            "NF_AUTORIZADA_PEDIDO_NAO_CONFIRMADO",
            "NF_ENCONTRADA_SEM_VINCULO_NO_PEDIDO",
            "PEDIDO_DUPLICADO_POR_NUMERO_LOJA",
        ],
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido.pedido_bling_id,
        nf_bling_id=_nf_bling_id_pedido(pedido),
        resolution_note="Fluxo reconciliado manualmente pela operacao.",
    )
    db.commit()

    registrar_evento(
        tenant_id=tenant_id,
        source="manual",
        event_type="pedido.manual_reconciled",
        entity_type="pedido",
        status="ok",
        severity="info",
        message="Fluxo do pedido foi reconciliado manualmente pela operacao.",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido.pedido_bling_id,
        nf_bling_id=_nf_bling_id_pedido(pedido),
        payload={
            "numero_pedido_loja": numero_pedido_loja_do_payload(pedido),
            "nf_numero": _numero_nf_pedido(pedido),
            "consolidacao": consolidacao,
            "resultado": detalhes,
        },
        db=db,
        auto_fix_applied=False,
    )

    return {
        "success": True,
        "pedido_id": pedido.id,
        "pedido_bling_numero": _text(getattr(pedido, "pedido_bling_numero", None)),
        "numero_pedido_loja": numero_pedido_loja_do_payload(pedido),
        "nf_numero": _numero_nf_pedido(pedido),
        "detalhes": detalhes,
        "consolidacao": consolidacao,
    }
