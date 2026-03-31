from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_flow_monitor_models import BlingFlowEvent, BlingFlowIncident
from app.db import get_session
from app.nfe_cache_models import BlingNotaFiscalCache
from app.pedido_integrado_models import PedidoIntegrado
from app.services.bling_flow_monitor_service import (
    auditar_fluxo_bling,
    autocorrigir_incidente,
    obter_resumo_monitoramento,
    resolver_incidente_por_id,
)


router = APIRouter(prefix="/integracoes/bling/monitor", tags=["Integracao Bling - Monitor"])


def _texto(value):
    if value is None:
        return None
    texto = str(value).strip()
    return texto or None


def _nf_bling_id_valido(value):
    texto = _texto(value)
    if not texto or texto in {"0", "-1"}:
        return None
    return texto


def _dict(value):
    return value if isinstance(value, dict) else {}


def _primeiro_preenchido(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _serializar_data_monitor(dt):
    if not dt:
        return None
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def _numero_pedido_loja_pedido(pedido: PedidoIntegrado) -> str | None:
    payload = _dict(getattr(pedido, "payload", None))
    pedido_payload = _dict(payload.get("pedido"))
    webhook_payload = _dict(payload.get("webhook"))

    return _texto(
        _primeiro_preenchido(
            pedido_payload.get("numeroLoja"),
            pedido_payload.get("numeroPedidoLoja"),
            pedido_payload.get("numeroPedido"),
            webhook_payload.get("numeroLoja"),
            webhook_payload.get("numeroPedidoLoja"),
            payload.get("numeroLoja"),
            payload.get("numeroPedidoLoja"),
        )
    )


def _nf_numero_pedido(pedido: PedidoIntegrado) -> str | None:
    payload = _dict(getattr(pedido, "payload", None))
    ultima_nf = _dict(
        payload.get("ultima_nf")
        or _dict(payload.get("pedido")).get("notaFiscal")
        or _dict(payload.get("pedido")).get("nota")
        or _dict(payload.get("pedido")).get("nfe")
    )
    return _texto(ultima_nf.get("numero"))


def _numero_pedido_loja_payload(payload: dict | None) -> str | None:
    payload = _dict(payload)
    pedido_payload = _dict(payload.get("pedido"))
    webhook_payload = _dict(payload.get("webhook"))
    nf_payload = _dict(payload.get("nf"))

    return _texto(
        _primeiro_preenchido(
            payload.get("numero_pedido_loja"),
            _dict(payload.get("nf_detectada")).get("numero_pedido_loja"),
            nf_payload.get("numero_pedido_loja"),
            pedido_payload.get("numeroLoja"),
            pedido_payload.get("numeroPedidoLoja"),
            pedido_payload.get("numeroPedido"),
            webhook_payload.get("numeroLoja"),
            webhook_payload.get("numeroPedidoLoja"),
        )
    )


def _nf_numero_payload(payload: dict | None) -> str | None:
    payload = _dict(payload)
    return _texto(
        _primeiro_preenchido(
            payload.get("nf_numero"),
            _dict(payload.get("ultima_nf")).get("numero"),
            _dict(payload.get("nf")).get("numero"),
            _dict(payload.get("nf_detectada")).get("numero"),
        )
    )


def _mapa_numeros_pedidos(db: Session, tenant_id, registros: list[dict]) -> dict[tuple[int | None, str | None], dict[str, str | None]]:
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

    mapa: dict[tuple[int | None, str | None], dict[str, str | None]] = {}
    for pedido in query.all():
        info = {
            "pedido_bling_numero": pedido.pedido_bling_numero or pedido.pedido_bling_id,
            "numero_pedido_loja": _numero_pedido_loja_pedido(pedido),
            "nf_numero": _nf_numero_pedido(pedido),
            "pedido_status_atual": _texto(getattr(pedido, "status", None)),
        }
        mapa[(pedido.id, pedido.pedido_bling_id)] = info
        mapa[(pedido.id, None)] = info
        mapa[(None, pedido.pedido_bling_id)] = info
    return mapa


def _mapa_numeros_notas_cache(db: Session, tenant_id, registros: list[dict]) -> dict[str, dict[str, str | None]]:
    nf_bling_ids = {
        _texto(registro.get("nf_bling_id"))
        for registro in registros
        if _texto(registro.get("nf_bling_id"))
    }
    if not nf_bling_ids:
        return {}

    mapa: dict[str, dict[str, str | None]] = {}
    query = (
        db.query(BlingNotaFiscalCache)
        .filter(
            BlingNotaFiscalCache.tenant_id == tenant_id,
            BlingNotaFiscalCache.bling_id.in_(list(nf_bling_ids)),
        )
        .order_by(BlingNotaFiscalCache.id.desc())
    )
    for nota in query.all():
        chave = _texto(getattr(nota, "bling_id", None))
        if not chave or chave in mapa:
            continue
        detalhe = _dict(getattr(nota, "detalhe_payload", None))
        resumo = _dict(getattr(nota, "resumo_payload", None))
        mapa[chave] = {
            "nf_numero": _texto(
                _primeiro_preenchido(
                    getattr(nota, "numero", None),
                    detalhe.get("numero"),
                    resumo.get("numero"),
                )
            ),
            "numero_pedido_loja": _texto(getattr(nota, "numero_pedido_loja", None)),
        }
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
            "nf_bling_id": _nf_bling_id_valido(incidente.nf_bling_id),
            "sku": incidente.sku,
            "occurrences": incidente.occurrences,
            "first_seen_em": _serializar_data_monitor(incidente.first_seen_em),
            "last_seen_em": _serializar_data_monitor(incidente.last_seen_em),
            "resolved_em": _serializar_data_monitor(incidente.resolved_em),
            "details": incidente.details or {},
        }
        for incidente in incidentes
    ]
    mapa_numeros = _mapa_numeros_pedidos(db, tenant_id, registros)
    mapa_notas = _mapa_numeros_notas_cache(db, tenant_id, registros)
    for registro in registros:
        info = mapa_numeros.get(
            (registro.get("pedido_integrado_id"), registro.get("pedido_bling_id"))
        ) or mapa_numeros.get((registro.get("pedido_integrado_id"), None)) or mapa_numeros.get(
            (None, registro.get("pedido_bling_id"))
        )
        info_nf = mapa_notas.get(_texto(registro.get("nf_bling_id")) or "") or {}
        detalhes = _dict(registro.get("details"))
        registro["pedido_bling_numero"] = (
            _dict(info).get("pedido_bling_numero")
            or _texto(_primeiro_preenchido(detalhes.get("pedido_bling_numero"), _dict(detalhes.get("nf_detectada")).get("pedido_bling_numero")))
        )
        registro["numero_pedido_loja"] = (
            _dict(info).get("numero_pedido_loja")
            or _texto(_primeiro_preenchido(detalhes.get("numero_pedido_loja"), _dict(detalhes.get("nf_detectada")).get("numero_pedido_loja")))
            or _dict(info_nf).get("numero_pedido_loja")
        )
        registro["nf_numero"] = (
            _texto(_primeiro_preenchido(detalhes.get("nf_numero"), _dict(detalhes.get("nf_detectada")).get("numero")))
            or _dict(info_nf).get("nf_numero")
            or _dict(info).get("nf_numero")
        )
        registro["pedido_status_atual"] = _dict(info).get("pedido_status_atual")
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
            "nf_bling_id": _nf_bling_id_valido(evento.nf_bling_id),
            "sku": evento.sku,
            "auto_fix_applied": evento.auto_fix_applied,
            "processed_at": _serializar_data_monitor(evento.processed_at),
            "payload": evento.payload or {},
        }
        for evento in eventos
    ]
    mapa_numeros = _mapa_numeros_pedidos(db, tenant_id, registros)
    mapa_notas = _mapa_numeros_notas_cache(db, tenant_id, registros)
    for registro in registros:
        info = mapa_numeros.get(
            (registro.get("pedido_integrado_id"), registro.get("pedido_bling_id"))
        ) or mapa_numeros.get((registro.get("pedido_integrado_id"), None)) or mapa_numeros.get(
            (None, registro.get("pedido_bling_id"))
        )
        info_nf = mapa_notas.get(_texto(registro.get("nf_bling_id")) or "") or {}
        payload = _dict(registro.get("payload"))
        registro["pedido_bling_numero"] = (
            _dict(info).get("pedido_bling_numero")
            or _texto(_primeiro_preenchido(payload.get("pedido_bling_numero"), _dict(payload.get("pedido")).get("numero")))
        )
        registro["numero_pedido_loja"] = (
            _dict(info).get("numero_pedido_loja")
            or _numero_pedido_loja_payload(payload)
            or _dict(info_nf).get("numero_pedido_loja")
        )
        registro["nf_numero"] = (
            _nf_numero_payload(payload)
            or _dict(info_nf).get("nf_numero")
            or _dict(info).get("nf_numero")
        )
        registro["pedido_status_atual"] = _dict(info).get("pedido_status_atual") or _texto(payload.get("pedido_status_atual"))
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
        "resolved_em": _serializar_data_monitor(incidente.resolved_em),
    }
