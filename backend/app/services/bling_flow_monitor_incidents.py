from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.bling_flow_monitor_models import BlingFlowEvent, BlingFlowIncident
from app.db import SessionLocal
from app.pedido_integrado_models import PedidoIntegrado
from app.services.bling_flow_monitor_constants import (
    OPEN_INCIDENT_STATUSES,
    SEVERITY_RANK,
)
from app.services.bling_flow_monitor_diagnostics import (
    _numero_pedido_loja_pedido,
    _ultima_nf,
)
from app.services.bling_flow_monitor_utils import (
    _dict,
    _json_safe,
    _nf_bling_id_valido,
    _payload_with_correlation,
    _text,
    _utcnow,
    normalizar_data_evento_monitor,
)
from app.tenancy.rls import sync_rls_tenant as _default_sync_rls_tenant
from app.utils.logger import logger

SyncTenantFn = Callable[[Session, Any], None]


def _sync_bling_flow_rls(
    db: Session,
    tenant_id,
    *,
    sync_rls_tenant_fn: SyncTenantFn = _default_sync_rls_tenant,
) -> None:
    if tenant_id:
        sync_rls_tenant_fn(db, tenant_id)


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
    sync_rls_tenant_fn: SyncTenantFn = _default_sync_rls_tenant,
) -> int | None:
    own_session = db is None
    session = db or SessionLocal()

    try:
        _sync_bling_flow_rls(
            session,
            tenant_id,
            sync_rls_tenant_fn=sync_rls_tenant_fn,
        )
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
            payload=_payload_with_correlation(payload),
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
        logger.warning(
            f"[BLING FLOW MONITOR] Falha ao registrar evento {event_type}: {exc}"
        )
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
    sync_rls_tenant_fn: SyncTenantFn = _default_sync_rls_tenant,
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
        _sync_bling_flow_rls(
            session,
            tenant_id,
            sync_rls_tenant_fn=sync_rls_tenant_fn,
        )
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
    sync_rls_tenant_fn: SyncTenantFn = _default_sync_rls_tenant,
) -> BlingFlowIncident | None:
    _sync_bling_flow_rls(db, tenant_id, sync_rls_tenant_fn=sync_rls_tenant_fn)
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
    sync_rls_tenant_fn: SyncTenantFn = _default_sync_rls_tenant,
) -> int:
    _sync_bling_flow_rls(db, tenant_id, sync_rls_tenant_fn=sync_rls_tenant_fn)
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
    registrar_evento_fn: Callable[..., int | None] | None = None,
    resolver_incidentes_relacionados_fn: Callable[..., int] | None = None,
) -> int | None:
    registrar_evento_fn = registrar_evento_fn or registrar_evento
    resolver_incidentes_relacionados_fn = (
        resolver_incidentes_relacionados_fn or resolver_incidentes_relacionados
    )

    payload_extra = _dict(_json_safe(payload or {}))
    nf_contexto = _ultima_nf(getattr(pedido, "payload", None))
    nf_bling_id_resolvido = _nf_bling_id_valido(nf_bling_id) or _nf_bling_id_valido(
        nf_contexto.get("id")
    )
    payload_base = {
        "pedido_bling_numero": _text(getattr(pedido, "pedido_bling_numero", None)),
        "numero_pedido_loja": _numero_pedido_loja_pedido(pedido),
        "pedido_status_atual": _text(getattr(pedido, "status", None)),
        "nf_numero": _text(nf_numero) or _text(nf_contexto.get("numero")),
    }
    evento_id = registrar_evento_fn(
        tenant_id=pedido.tenant_id,
        source=source,
        event_type="invoice.linked_to_order",
        entity_type="nf",
        status=status,
        severity=severity,
        message=message or "NF vinculada ao pedido durante o processamento do evento",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido.pedido_bling_id,
        nf_bling_id=nf_bling_id_resolvido,
        payload={**payload_base, **payload_extra},
        processed_at=processed_at,
        db=db,
        auto_fix_applied=auto_fix_applied,
    )
    if db is not None:
        resolver_incidentes_relacionados_fn(
            db,
            tenant_id=pedido.tenant_id,
            codes=[
                "NF_SEM_PEDIDO_VINCULADO",
                "NF_SEM_PEDIDO_LOCAL",
                "NF_ENCONTRADA_SEM_VINCULO_NO_PEDIDO",
            ],
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido.pedido_bling_id,
            nf_bling_id=nf_bling_id_resolvido,
            resolution_note="NF vinculada posteriormente ao pedido correspondente.",
        )
    return evento_id


__all__ = [
    "_build_incident_key",
    "_pick_more_severe",
    "_sync_bling_flow_rls",
    "abrir_incidente",
    "registrar_evento",
    "registrar_vinculo_nf_pedido",
    "resolver_incidente_por_id",
    "resolver_incidentes_relacionados",
]
