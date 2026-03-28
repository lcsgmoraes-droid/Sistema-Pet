from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.bling_flow_monitor_models import BlingFlowEvent, BlingFlowIncident
from app.db import SessionLocal
from app.estoque.service import EstoqueService
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
    "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
    "SKU_MAPEADO_POR_CODIGO_BARRAS",
}
NF_AUTHORIZED_CODES = {2, 9}


def _utcnow() -> datetime:
    return datetime.utcnow()


def _text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "hex") and callable(getattr(value, "hex", None)):
        try:
            return str(value)
        except Exception:
            return None
    return value


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
        nf_bling_id or "",
        sku or "",
    ]
    return "|".join(parts)


def _pick_more_severe(current: str, incoming: str) -> str:
    if SEVERITY_RANK.get(incoming, 0) >= SEVERITY_RANK.get(current, 0):
        return incoming
    return current


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
    codigo = nf.get("situacao_codigo")
    try:
        if codigo is not None and int(codigo) in NF_AUTHORIZED_CODES:
            return True
    except (TypeError, ValueError):
        pass

    situacao = (nf.get("situacao") or nf.get("status") or "").strip().lower()
    return any(token in situacao for token in ("autoriz", "emitida", "emitido"))


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
    return {
        "code": code,
        "severity": severity,
        "title": title,
        "message": message,
        "suggested_action": suggested_action,
        "auto_fixable": auto_fixable,
        "pedido_integrado_id": pedido.id,
        "pedido_bling_id": _text(pedido.pedido_bling_id),
        "nf_bling_id": _text(nf_bling_id),
        "sku": _text(sku),
        "details": _json_safe(details or {}),
    }


def diagnosticar_pedido_integrado(
    pedido,
    itens,
    payload: dict | None,
    *,
    movimentacoes_saida: int,
    itens_sem_produto: list[dict] | None = None,
    itens_mapeados_por_barra: list[dict] | None = None,
) -> list[dict]:
    itens_sem_produto = itens_sem_produto or []
    itens_mapeados_por_barra = itens_mapeados_por_barra or []
    incidentes: list[dict] = []
    nf = _ultima_nf(payload)

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

    if pedido.status == "confirmado":
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
                        nf_bling_id=_text(nf.get("id")),
                    )
                )

        if itens_vendidos and movimentacoes_saida < len(itens_vendidos):
            incidentes.append(
                _make_incident(
                    "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
                    severity="critical",
                    title="Pedido confirmado sem baixa completa de estoque",
                    message=(
                        f"Existem {len(itens_vendidos)} item(ns) vendidos, mas apenas "
                        f"{movimentacoes_saida} movimentacao(oes) de saida para o pedido."
                    ),
                    suggested_action="Reconciliar as baixas pendentes do pedido confirmado.",
                    auto_fixable=True,
                    pedido=pedido,
                    nf_bling_id=_text(nf.get("id")),
                    details={
                        "itens_vendidos": len(itens_vendidos),
                        "movimentacoes_saida": movimentacoes_saida,
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
            nf_bling_id=_text(nf_bling_id),
            sku=_text(sku),
            payload=_json_safe(payload or {}),
            auto_fix_applied=auto_fix_applied,
            processed_at=_utcnow(),
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
                nf_bling_id=_text(nf_bling_id),
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
    from app.services.bling_nf_service import (
        buscar_produto_do_item,
        criar_produto_automatico_do_bling,
    )

    movimentos = db.query(EstoqueMovimentacao).filter(
        EstoqueMovimentacao.tenant_id == pedido.tenant_id,
        EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
        EstoqueMovimentacao.referencia_id == pedido.id,
        EstoqueMovimentacao.tipo == "saida",
    ).all()
    movimentos_por_produto = Counter(mov.produto_id for mov in movimentos if mov.produto_id)
    movimentos_consumidos = Counter()

    itens_confirmados = 0
    baixas_criadas = 0
    erros: list[str] = []
    agora = _utcnow()

    for item in itens:
        if not item.vendido_em:
            item.vendido_em = agora
            db.add(item)
            itens_confirmados += 1

        produto = buscar_produto_do_item(db=db, tenant_id=pedido.tenant_id, sku=item.sku)
        if not produto:
            produto = criar_produto_automatico_do_bling(db=db, tenant_id=pedido.tenant_id, sku=item.sku)
        if not produto:
            erros.append(f"produto_nao_encontrado:{item.sku}")
            continue

        if movimentos_consumidos[produto.id] < movimentos_por_produto[produto.id]:
            movimentos_consumidos[produto.id] += 1
            continue

        try:
            EstoqueService.baixar_estoque(
                produto_id=produto.id,
                quantidade=float(item.quantidade),
                motivo="venda_bling_auditoria",
                referencia_id=pedido.id,
                referencia_tipo="pedido_integrado",
                user_id=0,
                db=db,
                tenant_id=pedido.tenant_id,
                documento=pedido.pedido_bling_numero,
                observacao="Correcao automatica via auditoria do fluxo Bling",
            )
            baixas_criadas += 1
        except Exception as exc:
            erros.append(f"baixa_falhou:{item.sku}:{str(exc)[:120]}")

    pedido.status = "confirmado"
    pedido.confirmado_em = pedido.confirmado_em or agora
    db.add(pedido)

    return (itens_confirmados > 0 or baixas_criadas > 0) and not erros, {
        "itens_confirmados": itens_confirmados,
        "baixas_criadas": baixas_criadas,
        "erros": erros,
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

    for pedido in pedidos:
        try:
            itens = db.query(PedidoIntegradoItem).filter(
                PedidoIntegradoItem.pedido_integrado_id == pedido.id
            ).all()
            movimentacoes_saida = db.query(EstoqueMovimentacao).filter(
                EstoqueMovimentacao.tenant_id == pedido.tenant_id,
                EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
                EstoqueMovimentacao.referencia_id == pedido.id,
                EstoqueMovimentacao.tipo == "saida",
            ).count()

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

            incidentes = diagnosticar_pedido_integrado(
                pedido,
                itens,
                _dict(pedido.payload),
                movimentacoes_saida=movimentacoes_saida,
                itens_sem_produto=itens_sem_produto,
                itens_mapeados_por_barra=itens_mapeados_por_barra,
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
                "processed_at": evento.processed_at.isoformat() if evento.processed_at else None,
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
