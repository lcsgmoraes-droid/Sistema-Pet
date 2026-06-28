from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any, Callable

from sqlalchemy import or_
from sqlalchemy.orm import Session, configure_mappers

from app.bling_flow_monitor_models import BlingFlowEvent, BlingFlowIncident
from app.db import SessionLocal
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.services.bling_flow_monitor_autofix import autocorrigir_incidente
from app.services.bling_flow_monitor_constants import (
    MONITORED_INCIDENT_CODES,
    PEDIDO_MONITORED_INCIDENT_CODES,
)
from app.services.bling_flow_monitor_diagnostics import (
    _coerce_int,
    _contar_movimentacoes_saida_nf,
    _indexar_nfs_por_pedido_loja,
    _numero_pedido_loja_pedido,
    _obter_nfs_recentes_bling,
    _produto_por_sku,
    diagnosticar_pedido_integrado,
)
from app.services.bling_flow_monitor_incidents import (
    abrir_incidente,
    registrar_evento,
)
from app.services.bling_flow_monitor_utils import (
    _dict,
    _nf_bling_id_valido,
    _text,
    _utcnow,
    serializar_data_evento_monitor,
)
from app.services.pedido_integrado_duplicate_review_service import (
    listar_grupos_duplicados_pedido_loja,
)
from app.tenancy.rls import sync_rls_tenant as _default_sync_rls_tenant
from app.utils.correlation import operation_correlation_context
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


def _garantir_registry_sqlalchemy_auditoria() -> None:
    # A auditoria pode rodar fora do app.main, entao registra os modelos antes
    # de queries com relacionamentos declarados por string.
    import app.dre_plano_contas_models  # noqa: F401
    import app.financeiro_models  # noqa: F401
    import app.ia.aba7_extrato_models  # noqa: F401
    import app.ia.aba7_models  # noqa: F401
    import app.models  # noqa: F401
    import app.vendas_models  # noqa: F401

    configure_mappers()


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
    registrar_evento_fn: Callable[..., int | None] | None = None,
    abrir_incidente_fn: Callable[..., BlingFlowIncident | None] | None = None,
    autocorrigir_incidente_fn: Callable[..., dict] | None = None,
    sync_rls_tenant_fn: SyncTenantFn = _default_sync_rls_tenant,
) -> dict:
    registrar_evento_fn = registrar_evento_fn or registrar_evento
    abrir_incidente_fn = abrir_incidente_fn or abrir_incidente
    autocorrigir_incidente_fn = autocorrigir_incidente_fn or autocorrigir_incidente

    if not _correlation_context_applied:
        with operation_correlation_context("job.bling_flow_audit") as correlation_id:
            result = auditar_fluxo_bling(
                db,
                tenant_id=tenant_id,
                dias=dias,
                limite=limite,
                auto_fix=auto_fix,
                _correlation_context_applied=True,
                registrar_evento_fn=registrar_evento_fn,
                abrir_incidente_fn=abrir_incidente_fn,
                autocorrigir_incidente_fn=autocorrigir_incidente_fn,
                sync_rls_tenant_fn=sync_rls_tenant_fn,
            )
            result.setdefault("correlation_id", correlation_id)
            return result

    _garantir_registry_sqlalchemy_auditoria()
    _sync_bling_flow_rls(db, tenant_id, sync_rls_tenant_fn=sync_rls_tenant_fn)
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
                        registrar_evento_fn(
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
                incidente = abrir_incidente_fn(
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
                    resultado = autocorrigir_incidente_fn(db, incidente)
                    if resultado.get("success"):
                        auto_fix_sucessos += 1

            incidentes_resolvidos += _resolver_incidentes_ausentes(
                db, pedido, active_keys
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            registrar_evento_fn(
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

            incidente = abrir_incidente_fn(
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
                resultado = autocorrigir_incidente_fn(db, incidente)
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


def obter_resumo_monitoramento(
    db: Session,
    *,
    tenant_id=None,
    sync_rls_tenant_fn: SyncTenantFn = _default_sync_rls_tenant,
) -> dict:
    _sync_bling_flow_rls(db, tenant_id, sync_rls_tenant_fn=sync_rls_tenant_fn)
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
    *,
    dias: int = 7,
    limite: int = 300,
    auto_fix: bool = True,
    auditar_fluxo_bling_fn: Callable[..., dict] | None = None,
) -> dict:
    auditar_fluxo_bling_fn = auditar_fluxo_bling_fn or auditar_fluxo_bling
    db = SessionLocal()
    try:
        resultado = auditar_fluxo_bling_fn(
            db,
            dias=dias,
            limite=limite,
            auto_fix=auto_fix,
        )
        logger.info(
            "[BLING FLOW MONITOR] Auditoria concluida: "
            f"pedidos={resultado['pedidos_auditados']} "
            f"incidentes={resultado['incidentes_detectados']} "
            f"autofix={resultado['auto_fix_sucessos']}/{resultado['auto_fix_tentados']}"
        )
        return resultado
    finally:
        db.close()


__all__ = [
    "_garantir_registry_sqlalchemy_auditoria",
    "_resolver_incidentes_ausentes",
    "_resolver_incidentes_duplicidade_ausentes",
    "_sync_bling_flow_rls",
    "auditar_fluxo_bling",
    "executar_auditoria_background",
    "obter_resumo_monitoramento",
]
