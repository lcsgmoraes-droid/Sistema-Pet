"""Alertas resumidos do periodo exibidos no painel Ops."""

from typing import Any

from sqlalchemy.orm import Session

from app.services.error_event_reporter import SLOW_REQUEST_EVENT_MS
from app.services.ops_dashboard_actionable_alerts import (
    _last_failed_deploy_after_success,
)
from app.services.ops_dashboard_utils import _env_int, _tenant_names


def _build_alerts(
    *,
    db: Session,
    watchdog: dict[str, Any],
    error_summary: dict[str, Any],
    deploy_events: list[dict[str, Any]],
    watchdog_summary: dict[str, Any],
    tenant_incidents: list[dict[str, Any]],
    route_incidents: list[dict[str, Any]],
    queue_snapshot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    errors_5xx = int(error_summary.get("errors_5xx") or 0)
    slow_requests = int(error_summary.get("slow_requests") or 0)
    last_failed = _last_failed_deploy_after_success(deploy_events)
    recoveries = int(watchdog_summary.get("recoveries") or 0)

    if watchdog.get("status") != "healthy":
        alerts.append(
            {
                "severity": "critical",
                "tone": "red",
                "title": "Watchdog degradado",
                "detail": "O banco ou o pool nao respondeu dentro do limite operacional.",
                "action": "Acompanhar eventos do watchdog; se repetir, revisar pool, banco e rotas lentas.",
                "source": "watchdog",
            }
        )

    if errors_5xx:
        top_route = route_incidents[0]["path"] if route_incidents else "rotas com erro"
        top_tenant = (
            tenant_incidents[0]["tenant_name"] if tenant_incidents else "tenant afetado"
        )
        alerts.append(
            {
                "severity": "critical",
                "tone": "red",
                "title": f"{errors_5xx} erro(s) 5xx no periodo",
                "detail": f"Maior incidencia em {top_route}; tenant em destaque: {top_tenant}.",
                "action": "Abrir a rota critica, localizar request_id e corrigir a causa raiz.",
                "source": "error_events",
            }
        )

    if slow_requests:
        alerts.append(
            {
                "severity": "warning",
                "tone": "amber",
                "title": f"{slow_requests} requisicao(oes) lenta(s)",
                "detail": f"Acima de {int(SLOW_REQUEST_EVENT_MS)} ms.",
                "action": "Priorizar rotas com maior tempo maximo e tenants com recorrencia.",
                "source": "slow_requests",
            }
        )

    if last_failed:
        alerts.append(
            {
                "severity": "critical",
                "tone": "red",
                "title": "Ultimo deploy falhou",
                "detail": last_failed.get("message")
                or f"Etapa: {last_failed.get('step') or '-'}",
                "action": "Nao seguir com novo deploy sem entender a falha anterior.",
                "source": "deploy",
            }
        )

    if recoveries:
        alerts.append(
            {
                "severity": "warning",
                "tone": "amber",
                "title": f"{recoveries} recuperacao(oes) automatica(s)",
                "detail": "O watchdog precisou reiniciar o servidor no periodo.",
                "action": "Verificar eventos anteriores ao restart e identificar o gatilho.",
                "source": "watchdog_events",
            }
        )

    if queue_snapshot:
        dead = int(queue_snapshot.get("dead") or 0)
        failed = int(queue_snapshot.get("failed") or 0)
        pending = int(queue_snapshot.get("pending") or 0)
        pending_warning = _env_int("OPS_BLING_PEDIDO_QUEUE_PENDING_WARNING", 50)
        by_tenant = queue_snapshot.get("by_tenant") or []
        tenant_names = _tenant_names(
            db,
            {
                str(item.get("tenant_id") or item.get("tenant_key") or "")
                for item in by_tenant
                if item.get("tenant_id") or item.get("tenant_key")
            },
        )

        if dead:
            alerts.append(
                {
                    "severity": "critical",
                    "tone": "red",
                    "title": f"{dead} webhook(s) Bling sem retry",
                    "detail": "A fila de pedidos do Bling tem eventos em dead letter.",
                    "action": "Abrir a fila bling_pedido_webhook_events, corrigir last_error e reenfileirar os eventos afetados.",
                    "source": "bling_pedido_queue",
                }
            )
        elif failed:
            alerts.append(
                {
                    "severity": "warning",
                    "tone": "amber",
                    "title": f"{failed} webhook(s) Bling aguardando retry",
                    "detail": "O worker vai tentar novamente com backoff.",
                    "action": "Acompanhar last_error; se repetir, tratar API Bling, token ou regra local antes de escalar tenants.",
                    "source": "bling_pedido_queue",
                }
            )
        elif pending >= pending_warning:
            alerts.append(
                {
                    "severity": "warning",
                    "tone": "amber",
                    "title": f"{pending} webhook(s) Bling pendente(s)",
                    "detail": f"Fila acima do limite operacional de {pending_warning}.",
                    "action": "Aumentar workers/limite do worker Bling ou investigar gargalo externo.",
                    "source": "bling_pedido_queue",
                }
            )

        for item in by_tenant[:5]:
            tenant_key = str(
                item.get("tenant_id") or item.get("tenant_key") or "sem_tenant"
            )
            pending_tenant = int(item.get("pending") or 0)
            processing_tenant = int(item.get("processing") or 0)
            failed_tenant = int(item.get("failed") or 0)
            dead_tenant = int(item.get("dead") or 0)
            total_open = int(item.get("total_open") or 0)
            if total_open <= 0:
                continue
            if not (
                dead_tenant
                or failed_tenant
                or pending_tenant >= pending_warning
                or tenant_key == "sem_tenant"
            ):
                continue

            tenant_name = tenant_names.get(tenant_key) or (
                "Sem tenant identificado"
                if tenant_key == "sem_tenant"
                else f"Tenant {tenant_key[:8]}"
            )
            severity = (
                "critical" if dead_tenant or tenant_key == "sem_tenant" else "warning"
            )
            alerts.append(
                {
                    "severity": severity,
                    "tone": "red" if severity == "critical" else "amber",
                    "title": f"Fila Bling em {tenant_name}: {total_open} pendencia(s)",
                    "detail": f"Pendentes {pending_tenant}, processando {processing_tenant}, retry {failed_tenant}, dead {dead_tenant}.",
                    "action": "Filtrar por tenant e tratar os eventos da fila antes de escalar novos tenants.",
                    "source": "bling_pedido_queue_tenant",
                    "tenant_id": None if tenant_key == "sem_tenant" else tenant_key,
                    "tenant_name": tenant_name,
                }
            )

    if not alerts:
        alerts.append(
            {
                "severity": "ok",
                "tone": "green",
                "title": "Sem alerta critico no periodo",
                "detail": "Health, deploys, erros e recuperacao automatica estao dentro do esperado.",
                "action": "Manter monitoramento.",
                "source": "ops",
            }
        )

    return alerts
