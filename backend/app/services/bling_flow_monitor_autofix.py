from __future__ import annotations

from sqlalchemy.orm import Session

from app.bling_flow_monitor_models import BlingFlowIncident
from app.nfe_cache_models import BlingNotaFiscalCache
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.services.bling_flow_monitor_diagnostics import (
    _loja_id_nf_contexto,
    _loja_id_pedido_integrado,
    _nf_contexto_autorizado,
    _numero_pedido_loja_pedido,
    _ultima_nf,
)
from app.services.bling_flow_monitor_utils import (
    _coerce_int,
    _dict,
    _json_safe,
    _nf_bling_id_valido,
    _primeiro_preenchido,
    _text,
    _utcnow,
)
from app.services.pedido_integrado_consolidation_service import (
    localizar_pedido_por_bling_id,
)
from app.services.pedido_integrado_duplicate_review_service import (
    consolidar_duplicidades_seguras_pedido,
)


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
        from app.integracao_bling_nf_routes import (
            _consultar_relacao_nf_bling,
            _registrar_nf_no_pedido,
        )
        from app.services.bling_nf_service import (
            processar_nf_autorizada,
            processar_nf_cancelada,
        )

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

        itens = (
            db.query(PedidoIntegradoItem)
            .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
            .all()
        )

        acao = None
        if _nf_contexto_autorizado(nf_detectada):
            acao = processar_nf_autorizada(
                db=db, pedido=pedido, itens=itens, nf_id=nf_id
            )
        elif situacao_num == 4:
            acao = processar_nf_cancelada(db=db, pedido=pedido, itens=itens)

        from app.services.bling_flow_monitor_service import registrar_vinculo_nf_pedido

        registrar_vinculo_nf_pedido(
            pedido=pedido,
            source="autofix",
            nf_bling_id=nf_id,
            nf_numero=_text(dados_nf.get("numero"))
            or _text(nf_detectada.get("numero")),
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
            "nf_numero": _text(dados_nf.get("numero"))
            or _text(nf_detectada.get("numero")),
            "acao": _json_safe(acao),
        }
    except Exception as exc:
        return False, {"motivo": "falha_vinculo_nf_detectada", "erro": str(exc)}


def _recarregar_itens_do_pedido(
    db: Session, pedido: PedidoIntegrado
) -> tuple[bool, dict]:
    from app.bling_integration import BlingAPI
    from app.estoque_reserva_service import EstoqueReservaService

    pedido_completo = BlingAPI().consultar_pedido(pedido.pedido_bling_id)
    itens_bling = pedido_completo.get("itens") or []
    if not itens_bling:
        return False, {"motivo": "bling_sem_itens"}

    if not isinstance(pedido.payload, dict):
        pedido.payload = {}
    pedido.payload["pedido"] = pedido_completo

    existentes = (
        db.query(PedidoIntegradoItem)
        .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
        .count()
    )
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


def _liberar_reservas_pedido_finalizado(
    db: Session, pedido: PedidoIntegrado, itens: list[PedidoIntegradoItem]
) -> tuple[bool, dict]:
    liberados = 0
    agora = _utcnow()
    for item in itens:
        if item.liberado_em or item.vendido_em:
            continue
        item.liberado_em = agora
        db.add(item)
        liberados += 1
    return liberados > 0, {"itens_liberados": liberados}


def _reconciliar_pedido_confirmado(
    db: Session, pedido: PedidoIntegrado, itens: list[PedidoIntegradoItem]
) -> tuple[bool, dict]:
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
            if nf_cache and not _nf_contexto_autorizado(
                {"situacao": getattr(nf_cache, "status", None)}
            ):
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
                    if _nf_contexto_autorizado(
                        {"situacao": getattr(nota, "status", None)}
                    )
                ]
                if loja_id_pedido:
                    notas_loja = [
                        nota
                        for nota in notas_loja
                        if not _loja_id_nf_contexto(
                            _dict(getattr(nota, "detalhe_payload", None))
                            or _dict(getattr(nota, "resumo_payload", None))
                        )
                        or _loja_id_nf_contexto(
                            _dict(getattr(nota, "detalhe_payload", None))
                            or _dict(getattr(nota, "resumo_payload", None))
                        )
                        == loja_id_pedido
                    ]
                notas_unicas: dict[str, BlingNotaFiscalCache] = {}
                for nota in notas_loja:
                    pedido_ref_nota = _text(getattr(nota, "pedido_bling_id_ref", None))
                    if pedido_ref_nota and pedido_ref_nota != _text(
                        getattr(pedido, "pedido_bling_id", None)
                    ):
                        continue
                    chave = (
                        _nf_bling_id_valido(getattr(nota, "bling_id", None))
                        or _text(getattr(nota, "numero", None))
                        or ""
                    )
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
        nf_id = _nf_bling_id_valido(
            _primeiro_preenchido(nf.get("id"), nf.get("nfe_id"))
        )
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
    if acao == "nf_vinculada_outro_pedido":
        return True, {
            "acao": acao,
            "nf_id": nf_id,
            "motivo": "nf_incorreta_removida_do_pedido",
        }
    return acao in {"venda_confirmada", "venda_ja_confirmada"}, {
        "acao": acao,
        "nf_id": nf_id,
    }


def autocorrigir_incidente(db: Session, incidente: BlingFlowIncident) -> dict:
    from app.services.bling_nf_service import criar_produto_automatico_do_bling

    pedido = None
    if incidente.pedido_integrado_id:
        pedido = (
            db.query(PedidoIntegrado)
            .filter(
                PedidoIntegrado.id == incidente.pedido_integrado_id,
                PedidoIntegrado.tenant_id == incidente.tenant_id,
            )
            .first()
        )
    if not pedido and incidente.pedido_bling_id:
        pedido = localizar_pedido_por_bling_id(
            db,
            tenant_id=incidente.tenant_id,
            pedido_bling_id=incidente.pedido_bling_id,
        )

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
            itens = (
                db.query(PedidoIntegradoItem)
                .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
                .all()
            )
            sucesso, detalhes = _liberar_reservas_pedido_finalizado(db, pedido, itens)
        elif pedido and incidente.code in {
            "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
            "NF_AUTORIZADA_PEDIDO_NAO_CONFIRMADO",
            "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
        }:
            itens = (
                db.query(PedidoIntegradoItem)
                .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
                .all()
            )
            sucesso, detalhes = _reconciliar_pedido_confirmado(db, pedido, itens)
        elif pedido and incidente.code == "NF_ENCONTRADA_SEM_VINCULO_NO_PEDIDO":
            sucesso, detalhes = _vincular_nf_detectada_ao_pedido(
                db,
                pedido,
                _dict(_dict(incidente.details).get("nf_detectada")),
            )
        elif pedido and incidente.code == "PEDIDO_DUPLICADO_POR_NUMERO_LOJA":
            resultado = consolidar_duplicidades_seguras_pedido(
                db,
                tenant_id=incidente.tenant_id,
                pedido_id=pedido.id,
                source="autofix",
                auto_fix_applied=True,
                resolution_note="Duplicidades seguras consolidadas automaticamente pelo monitor.",
            )
            sucesso = bool(resultado.get("success"))
            detalhes = resultado
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

        from app.services.bling_flow_monitor_service import registrar_evento

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
