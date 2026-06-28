from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.bling_flow_monitor_models import BlingFlowIncident
from app.pedido_integrado_models import PedidoIntegrado
from app.services import bling_flow_monitor_auditoria as _auditoria
from app.services import bling_flow_monitor_incidents as _incidents
from app.services.bling_flow_monitor_autofix import (
    _liberar_reservas_pedido_finalizado,
    _recarregar_itens_do_pedido,
    _reconciliar_pedido_confirmado,
    _vincular_nf_detectada_ao_pedido,
    autocorrigir_incidente,
)
from app.services.bling_flow_monitor_constants import (
    FINAL_STATUS,
    MONITORED_INCIDENT_CODES,
    OPEN_INCIDENT_STATUSES,
    PEDIDO_MONITORED_INCIDENT_CODES,
    SEVERITY_RANK,
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
from app.services.bling_flow_monitor_incidents import (
    _build_incident_key,
    _pick_more_severe,
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
    "_garantir_registry_sqlalchemy_auditoria",
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
    "_sync_bling_flow_rls",
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
    return _incidents._sync_bling_flow_rls(
        db,
        tenant_id,
        sync_rls_tenant_fn=sync_rls_tenant,
    )


def _garantir_registry_sqlalchemy_auditoria() -> None:
    return _auditoria._garantir_registry_sqlalchemy_auditoria()


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
    return _incidents.registrar_evento(
        tenant_id=tenant_id,
        source=source,
        event_type=event_type,
        entity_type=entity_type,
        status=status,
        severity=severity,
        message=message,
        error_message=error_message,
        pedido_integrado_id=pedido_integrado_id,
        pedido_bling_id=pedido_bling_id,
        nf_bling_id=nf_bling_id,
        sku=sku,
        payload=payload,
        auto_fix_applied=auto_fix_applied,
        processed_at=processed_at,
        db=db,
        sync_rls_tenant_fn=sync_rls_tenant,
    )


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
    return _incidents.abrir_incidente(
        tenant_id=tenant_id,
        code=code,
        severity=severity,
        title=title,
        message=message,
        suggested_action=suggested_action,
        auto_fixable=auto_fixable,
        pedido_integrado_id=pedido_integrado_id,
        pedido_bling_id=pedido_bling_id,
        nf_bling_id=nf_bling_id,
        sku=sku,
        details=details,
        source=source,
        scope=scope,
        db=db,
        sync_rls_tenant_fn=sync_rls_tenant,
    )


def resolver_incidente_por_id(
    db: Session,
    tenant_id,
    incidente_id: int,
    *,
    resolution_note: str | None = None,
) -> BlingFlowIncident | None:
    return _incidents.resolver_incidente_por_id(
        db,
        tenant_id,
        incidente_id,
        resolution_note=resolution_note,
        sync_rls_tenant_fn=sync_rls_tenant,
    )


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
    return _incidents.resolver_incidentes_relacionados(
        db,
        tenant_id=tenant_id,
        codes=codes,
        pedido_integrado_id=pedido_integrado_id,
        pedido_bling_id=pedido_bling_id,
        nf_bling_id=nf_bling_id,
        resolution_note=resolution_note,
        sync_rls_tenant_fn=sync_rls_tenant,
    )


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
    return _incidents.registrar_vinculo_nf_pedido(
        pedido=pedido,
        source=source,
        nf_bling_id=nf_bling_id,
        nf_numero=nf_numero,
        status=status,
        severity=severity,
        message=message,
        payload=payload,
        processed_at=processed_at,
        db=db,
        auto_fix_applied=auto_fix_applied,
        registrar_evento_fn=registrar_evento,
        resolver_incidentes_relacionados_fn=resolver_incidentes_relacionados,
    )


def auditar_fluxo_bling(
    db: Session,
    *,
    tenant_id=None,
    dias: int = 7,
    limite: int = 300,
    auto_fix: bool = True,
    _correlation_context_applied: bool = False,
) -> dict:
    return _auditoria.auditar_fluxo_bling(
        db,
        tenant_id=tenant_id,
        dias=dias,
        limite=limite,
        auto_fix=auto_fix,
        _correlation_context_applied=_correlation_context_applied,
        registrar_evento_fn=registrar_evento,
        abrir_incidente_fn=abrir_incidente,
        autocorrigir_incidente_fn=autocorrigir_incidente,
        sync_rls_tenant_fn=sync_rls_tenant,
    )


def obter_resumo_monitoramento(db: Session, *, tenant_id=None) -> dict:
    return _auditoria.obter_resumo_monitoramento(
        db,
        tenant_id=tenant_id,
        sync_rls_tenant_fn=sync_rls_tenant,
    )


def executar_auditoria_background(
    *, dias: int = 7, limite: int = 300, auto_fix: bool = True
) -> dict:
    return _auditoria.executar_auditoria_background(
        dias=dias,
        limite=limite,
        auto_fix=auto_fix,
        auditar_fluxo_bling_fn=auditar_fluxo_bling,
    )
