from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_flow_monitor_models import BlingFlowEvent, BlingFlowIncident
from app.db import get_session
from app.pedido_integrado_models import PedidoIntegrado
from app.services.bling_flow_monitor_service import (
    auditar_fluxo_bling,
    autocorrigir_incidente,
    obter_resumo_monitoramento,
    resolver_incidente_por_id,
)


router = APIRouter(prefix="/integracoes/bling/monitor", tags=["Integracao Bling - Monitor"])


def _mapa_numeros_pedidos(db: Session, tenant_id, registros: list[dict]) -> dict[tuple[int | None, str | None], str | None]:
    pedido_ids = {registro.get("pedido_integrado_id") for registro in registros if registro.get("pedido_integrado_id")}
    pedido_bling_ids = {registro.get("pedido_bling_id") for registro in registros if registro.get("pedido_bling_id")}

    if not pedido_ids and not pedido_bling_ids:
        return {}

    query = db.query(PedidoIntegrado).filter(PedidoIntegrado.tenant_id == tenant_id)
    if pedido_ids:
        query = query.filter(
            (PedidoIntegrado.id.in_(pedido_ids)) | (PedidoIntegrado.pedido_bling_id.in_(pedido_bling_ids))
        )
    else:
        query = query.filter(PedidoIntegrado.pedido_bling_id.in_(pedido_bling_ids))

    mapa: dict[tuple[int | None, str | None], str | None] = {}
    for pedido in query.all():
        numero = pedido.pedido_bling_numero or pedido.pedido_bling_id
        mapa[(pedido.id, pedido.pedido_bling_id)] = numero
        mapa[(pedido.id, None)] = numero
        mapa[(None, pedido.pedido_bling_id)] = numero
    return mapa


@router.get("/resumo")
def resumo_monitor(
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    return obter_resumo_monitoramento(db, tenant_id=tenant_id)


@router.get("/incidentes")
def listar_incidentes(
    status: str = Query("open"),
    severidade: str | None = Query(None),
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    query = db.query(BlingFlowIncident).filter(BlingFlowIncident.tenant_id == tenant_id)
    if status:
        query = query.filter(BlingFlowIncident.status == status)
    if severidade:
        query = query.filter(BlingFlowIncident.severity == severidade)

    incidentes = (
        query.order_by(BlingFlowIncident.last_seen_em.desc(), BlingFlowIncident.id.desc())
        .limit(limite)
        .all()
    )
    registros = [
        {
            "id": incidente.id,
            "code": incidente.code,
            "severity": incidente.severity,
            "status": incidente.status,
            "title": incidente.title,
            "message": incidente.message,
            "suggested_action": incidente.suggested_action,
            "auto_fixable": incidente.auto_fixable,
            "auto_fix_status": incidente.auto_fix_status,
            "pedido_integrado_id": incidente.pedido_integrado_id,
            "pedido_bling_id": incidente.pedido_bling_id,
            "nf_bling_id": incidente.nf_bling_id,
            "sku": incidente.sku,
            "occurrences": incidente.occurrences,
            "first_seen_em": incidente.first_seen_em.isoformat() if incidente.first_seen_em else None,
            "last_seen_em": incidente.last_seen_em.isoformat() if incidente.last_seen_em else None,
            "resolved_em": incidente.resolved_em.isoformat() if incidente.resolved_em else None,
            "details": incidente.details or {},
        }
        for incidente in incidentes
    ]
    mapa_numeros = _mapa_numeros_pedidos(db, tenant_id, registros)
    for registro in registros:
        registro["pedido_bling_numero"] = mapa_numeros.get(
            (registro.get("pedido_integrado_id"), registro.get("pedido_bling_id"))
        ) or mapa_numeros.get((registro.get("pedido_integrado_id"), None)) or mapa_numeros.get(
            (None, registro.get("pedido_bling_id"))
        )
    return registros


@router.get("/eventos")
def listar_eventos(
    limite: int = Query(50, ge=1, le=200),
    tipo: str | None = Query(None),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    query = db.query(BlingFlowEvent).filter(BlingFlowEvent.tenant_id == tenant_id)
    if tipo:
        query = query.filter(BlingFlowEvent.event_type == tipo)

    eventos = (
        query.order_by(BlingFlowEvent.processed_at.desc(), BlingFlowEvent.id.desc())
        .limit(limite)
        .all()
    )
    registros = [
        {
            "id": evento.id,
            "source": evento.source,
            "event_type": evento.event_type,
            "entity_type": evento.entity_type,
            "status": evento.status,
            "severity": evento.severity,
            "message": evento.message,
            "error_message": evento.error_message,
            "pedido_integrado_id": evento.pedido_integrado_id,
            "pedido_bling_id": evento.pedido_bling_id,
            "nf_bling_id": evento.nf_bling_id,
            "sku": evento.sku,
            "auto_fix_applied": evento.auto_fix_applied,
            "processed_at": evento.processed_at.isoformat() if evento.processed_at else None,
            "payload": evento.payload or {},
        }
        for evento in eventos
    ]
    mapa_numeros = _mapa_numeros_pedidos(db, tenant_id, registros)
    for registro in registros:
        registro["pedido_bling_numero"] = mapa_numeros.get(
            (registro.get("pedido_integrado_id"), registro.get("pedido_bling_id"))
        ) or mapa_numeros.get((registro.get("pedido_integrado_id"), None)) or mapa_numeros.get(
            (None, registro.get("pedido_bling_id"))
        )
    return registros


@router.post("/auditar")
def executar_auditoria(
    dias: int = Query(7, ge=1, le=30),
    limite: int = Query(300, ge=1, le=1000),
    auto_fix: bool = Query(True),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    return auditar_fluxo_bling(
        db,
        tenant_id=tenant_id,
        dias=dias,
        limite=limite,
        auto_fix=auto_fix,
    )


@router.post("/incidentes/{incidente_id}/corrigir")
def corrigir_incidente(
    incidente_id: int,
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    incidente = db.query(BlingFlowIncident).filter(
        BlingFlowIncident.id == incidente_id,
        BlingFlowIncident.tenant_id == tenant_id,
    ).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente nao encontrado")
    if not incidente.auto_fixable:
        raise HTTPException(status_code=400, detail="Incidente sem autocorrecao disponivel")
    return autocorrigir_incidente(db, incidente)


@router.post("/incidentes/{incidente_id}/resolver")
def resolver_incidente(
    incidente_id: int,
    nota: str | None = Query(None),
    db: Session = Depends(get_session),
    user_tenant=Depends(get_current_user_and_tenant),
):
    tenant_id = user_tenant[1]
    incidente = resolver_incidente_por_id(db, tenant_id, incidente_id, resolution_note=nota)
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente nao encontrado")
    return {
        "status": "ok",
        "incidente_id": incidente.id,
        "resolved_em": incidente.resolved_em.isoformat() if incidente.resolved_em else None,
    }
