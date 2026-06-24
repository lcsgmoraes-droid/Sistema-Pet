from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session, configure_mappers

from app.bling_flow_monitor_models import BlingFlowEvent, BlingFlowIncident
from app.db import SessionLocal
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.services.pedido_integrado_duplicate_review_service import (
    listar_grupos_duplicados_pedido_loja,
)
from app.services.bling_flow_monitor_diagnostics import (
    NF_AUTHORIZED_CODES,
    _canal_pedido_integrado,
    _coerce_int,
    _contar_movimentacoes_saida_nf,
    _indexar_nfs_por_pedido_loja,
    _loja_id_nf_contexto,
    _loja_id_pedido_integrado,
    _nf_autorizada,
    _nf_contexto_autorizado,
    _nf_detectada_combina_com_pedido,
    _nf_recentes_cache,
    _numero_pedido_loja_pedido,
    _obter_nfs_recentes_bling,
    _pedido_total,
    _produto_por_sku,
    _ultima_nf,
    diagnosticar_pedido_integrado,
)
from app.services.bling_flow_monitor_autofix import (
    _liberar_reservas_pedido_finalizado,
    _recarregar_itens_do_pedido,
    _reconciliar_pedido_confirmado,
    _vincular_nf_detectada_ao_pedido,
    autocorrigir_incidente,
)
from app.services.bling_flow_monitor_utils import (
    _dict,
    _json_safe,
    _nf_bling_id_valido,
    _normalizar_contexto_nf,
    _payload_with_correlation,
    _primeiro_preenchido,
    _text,
    _utcnow,
    normalizar_data_evento_monitor,
    serializar_data_evento_monitor,
)
from app.tenancy.rls import sync_rls_tenant
from app.utils.correlation import operation_correlation_context
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
PEDIDO_MONITORED_INCIDENT_CODES = {
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
EXTRA_MONITORED_INCIDENT_CODES = {
    "PEDIDO_DUPLICADO_POR_NUMERO_LOJA",
}
MONITORED_INCIDENT_CODES = (
    PEDIDO_MONITORED_INCIDENT_CODES | EXTRA_MONITORED_INCIDENT_CODES
)

__all__ = [
    "FINAL_STATUS",
    "MONITORED_INCIDENT_CODES",
    "NF_AUTHORIZED_CODES",
    "OPEN_INCIDENT_STATUSES",
    "PEDIDO_MONITORED_INCIDENT_CODES",
    "SEVERITY_RANK",
    "_build_incident_key",
    "_canal_pedido_integrado",
    "_coerce_int",
    "_contar_movimentacoes_saida_nf",
    "_dict",
    "_indexar_nfs_por_pedido_loja",
    "_json_safe",
    "_liberar_reservas_pedido_finalizado",
    "_loja_id_nf_contexto",
    "_loja_id_pedido_integrado",
    "_nf_autorizada",
    "_nf_bling_id_valido",
    "_nf_contexto_autorizado",
    "_nf_detectada_combina_com_pedido",
    "_nf_recentes_cache",
    "_normalizar_contexto_nf",
    "_numero_pedido_loja_pedido",
    "_obter_nfs_recentes_bling",
    "_payload_with_correlation",
    "_pedido_total",
    "_pick_more_severe",
    "_primeiro_preenchido",
    "_produto_por_sku",
    "_recarregar_itens_do_pedido",
    "_reconciliar_pedido_confirmado",
    "_text",
    "_ultima_nf",
    "_utcnow",
    "_vincular_nf_detectada_ao_pedido",
    "abrir_incidente",
    "auditar_fluxo_bling",
    "autocorrigir_incidente",
    "diagnosticar_pedido_integrado",
    "executar_auditoria_background",
    "normalizar_data_evento_monitor",
    "obter_resumo_monitoramento",
    "registrar_evento",
    "registrar_vinculo_nf_pedido",
    "resolver_incidente_por_id",
    "resolver_incidentes_relacionados",
    "serializar_data_evento_monitor",
]


def _sync_bling_flow_rls(db: Session, tenant_id) -> None:
    if tenant_id:
        sync_rls_tenant(db, tenant_id)


def _garantir_registry_sqlalchemy_auditoria() -> None:
    # A auditoria pode rodar fora do app.main (script/scheduler/manual),
    # então ela precisa bootstrapar explicitamente os modelos com relacionamentos
    # declarados por string antes de qualquer query.
    import app.models  # noqa: F401
    import app.vendas_models  # noqa: F401
    import app.financeiro_models  # noqa: F401
    import app.dre_plano_contas_models  # noqa: F401
    import app.ia.aba7_extrato_models  # noqa: F401
    import app.ia.aba7_models  # noqa: F401

    configure_mappers()


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
    nf_bling_id_resolvido = _nf_bling_id_valido(nf_bling_id) or _nf_bling_id_valido(
        nf_contexto.get("id")
    )
    payload_base = {
        "pedido_bling_numero": _text(getattr(pedido, "pedido_bling_numero", None)),
        "numero_pedido_loja": _numero_pedido_loja_pedido(pedido),
        "pedido_status_atual": _text(getattr(pedido, "status", None)),
        "nf_numero": _text(nf_numero) or _text(nf_contexto.get("numero")),
    }
    evento_id = registrar_evento(
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
        resolver_incidentes_relacionados(
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
) -> int | None:
    own_session = db is None
    session = db or SessionLocal()

    try:
        _sync_bling_flow_rls(session, tenant_id)
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
        _sync_bling_flow_rls(session, tenant_id)
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
    _sync_bling_flow_rls(db, tenant_id)
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
    _sync_bling_flow_rls(db, tenant_id)
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
            BlingFlowIncident.code.in_(list(PEDIDO_MONITORED_INCIDENT_CODES)),
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


def _resolver_incidentes_duplicidade_ausentes(
    db: Session,
    *,
    tenant_id,
    active_keys: set[str],
) -> int:
    incidentes = (
        db.query(BlingFlowIncident)
        .filter(
            BlingFlowIncident.tenant_id == tenant_id,
            BlingFlowIncident.source == "auditoria",
            BlingFlowIncident.status == "open",
            BlingFlowIncident.code == "PEDIDO_DUPLICADO_POR_NUMERO_LOJA",
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


def auditar_fluxo_bling(
    db: Session,
    *,
    tenant_id=None,
    dias: int = 7,
    limite: int = 300,
    auto_fix: bool = True,
    _correlation_context_applied: bool = False,
) -> dict:
    if not _correlation_context_applied:
        with operation_correlation_context("job.bling_flow_audit") as correlation_id:
            result = auditar_fluxo_bling(
                db,
                tenant_id=tenant_id,
                dias=dias,
                limite=limite,
                auto_fix=auto_fix,
                _correlation_context_applied=True,
            )
            result.setdefault("correlation_id", correlation_id)
            return result

    _garantir_registry_sqlalchemy_auditoria()
    _sync_bling_flow_rls(db, tenant_id)
    cutoff = _utcnow() - timedelta(days=max(1, dias))
    query = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.criado_em >= cutoff,
        PedidoIntegrado.status != "mesclado",
    )
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
            itens = (
                db.query(PedidoIntegradoItem)
                .filter(PedidoIntegradoItem.pedido_integrado_id == pedido.id)
                .all()
            )
            movimentacoes_saida, movimentacoes_saida_nf = (
                _contar_movimentacoes_saida_nf(
                    db,
                    pedido,
                    payload=_dict(pedido.payload),
                )
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
                and (pedido.status in {"aberto", "expirado", "confirmado"})
            )
            if precisa_auditar_nfs_recentes:
                if pedido.tenant_id not in nfs_recentes_por_tenant:
                    try:
                        notas_recentes = _obter_nfs_recentes_bling(
                            tenant_id=pedido.tenant_id,
                            dias=max(1, min(dias, 5)),
                            db=db,
                        )
                        nfs_recentes_por_tenant[pedido.tenant_id] = (
                            _indexar_nfs_por_pedido_loja(notas_recentes)
                        )
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
                nfs_detectadas = nfs_recentes_por_tenant.get(pedido.tenant_id, {}).get(
                    numero_pedido_loja, []
                )

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

            incidentes_resolvidos += _resolver_incidentes_ausentes(
                db, pedido, active_keys
            )
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

    tenant_ids_duplicidade = (
        {tenant_id}
        if tenant_id
        else {
            pedido.tenant_id for pedido in pedidos if getattr(pedido, "tenant_id", None)
        }
    )
    for duplicate_tenant_id in tenant_ids_duplicidade:
        duplicate_active_keys: set[str] = set()
        duplicate_groups = listar_grupos_duplicados_pedido_loja(
            db,
            tenant_id=duplicate_tenant_id,
            dias=max(int(dias or 0), 30),
            limite_scan=max(max(1, min(limite, 1000)) * 8, 2000),
        )
        for grupo in duplicate_groups:
            pedido_canonico = _dict(grupo.get("pedido_canonico"))
            pedido_canonico_id = _coerce_int(pedido_canonico.get("id"), 0) or None
            pedido_canonico_bling_id = _text(pedido_canonico.get("pedido_bling_id"))
            nf_bling_id = _nf_bling_id_valido(pedido_canonico.get("nf_bling_id"))
            nf_numero = _text(pedido_canonico.get("nf_numero"))
            numero_pedido_loja = _text(grupo.get("numero_pedido_loja"))
            seguros = grupo.get("pedidos_seguro_ids") or []
            bloqueados = grupo.get("pedidos_bloqueados_ids") or []

            incidente = abrir_incidente(
                tenant_id=duplicate_tenant_id,
                code="PEDIDO_DUPLICADO_POR_NUMERO_LOJA",
                severity="high",
                title="Pedidos duplicados para o mesmo numero da loja",
                message=(
                    f"Foram encontrados {len(grupo.get('pedidos_duplicados') or []) + 1} pedidos locais para o numero "
                    f"da loja {numero_pedido_loja}. O sistema passou a tratar o pedido canonico, "
                    "mas o historico antigo precisa ser saneado para evitar ruido e reservas indevidas."
                ),
                suggested_action=(
                    "Consolidar os duplicados seguros no pedido canonico e revisar manualmente os casos com "
                    "movimentacao de estoque ou item vendido."
                ),
                auto_fixable=bool(seguros),
                pedido_integrado_id=pedido_canonico_id,
                pedido_bling_id=pedido_canonico_bling_id,
                nf_bling_id=nf_bling_id,
                details={
                    "numero_pedido_loja": numero_pedido_loja,
                    "nf_numero": nf_numero,
                    "pedido_canonico": grupo.get("pedido_canonico"),
                    "pedidos_duplicados": grupo.get("pedidos_duplicados") or [],
                    "pedidos_seguro_ids": seguros,
                    "pedidos_bloqueados_ids": bloqueados,
                    "bloqueios": grupo.get("bloqueios") or [],
                    "pode_consolidar_automaticamente": grupo.get(
                        "pode_consolidar_automaticamente", False
                    ),
                    "requer_revisao_manual": grupo.get("requer_revisao_manual", False),
                },
                source="auditoria",
                db=db,
            )
            if not incidente:
                continue
            duplicate_active_keys.add(incidente.dedupe_key)

            if auto_fix and incidente.auto_fixable and incidente.status == "open":
                auto_fix_tentados += 1
                resultado = autocorrigir_incidente(db, incidente)
                if resultado.get("success"):
                    auto_fix_sucessos += 1

        incidentes_resolvidos += _resolver_incidentes_duplicidade_ausentes(
            db,
            tenant_id=duplicate_tenant_id,
            active_keys=duplicate_active_keys,
        )
    db.commit()

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
    _sync_bling_flow_rls(db, tenant_id)
    incidentes_query = db.query(BlingFlowIncident).filter(
        BlingFlowIncident.status == "open"
    )
    eventos_query = db.query(BlingFlowEvent)
    if tenant_id:
        incidentes_query = incidentes_query.filter(
            BlingFlowIncident.tenant_id == tenant_id
        )
        eventos_query = eventos_query.filter(BlingFlowEvent.tenant_id == tenant_id)

    incidentes_abertos = incidentes_query.all()
    eventos_recentes = (
        eventos_query.order_by(
            BlingFlowEvent.processed_at.desc(),
            BlingFlowEvent.id.desc(),
        )
        .limit(10)
        .all()
    )

    por_severidade = Counter(inc.severity for inc in incidentes_abertos)
    por_codigo = Counter(inc.code for inc in incidentes_abertos)

    return {
        "status": "critical"
        if por_severidade.get("critical")
        else ("warning" if incidentes_abertos else "healthy"),
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


def executar_auditoria_background(
    *, dias: int = 7, limite: int = 300, auto_fix: bool = True
) -> dict:
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
