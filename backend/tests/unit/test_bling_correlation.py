from types import SimpleNamespace

from app.middlewares.request_context import clear_request_context, get_request_id, set_request_id
from app.utils.logger import clear_context


def teardown_function():
    clear_request_context()
    clear_context()


def test_bling_flow_payload_adds_active_correlation_without_overwriting():
    from app.services.bling_flow_monitor_service import _payload_with_correlation

    set_request_id("job-audit-123")

    payload = _payload_with_correlation({"pedido_bling_id": "BL-1", "correlation_id": "external"})

    assert payload["request_id"] == "job-audit-123"
    assert payload["correlation_id"] == "external"


def test_bling_webhook_event_correlation_is_stable_per_event():
    from app.services.bling_pedido_webhook_queue_service import _event_correlation_id

    event = SimpleNamespace(event_id="evt-123", dedupe_key="event:evt-123", id=10)

    first = _event_correlation_id(event)
    second = _event_correlation_id(event)

    assert first == second
    assert first.startswith("job.bling-pedido-webhook-")
    assert len(first) <= 80


def test_pedido_status_reconciliation_rate_limit_result_has_job_correlation(monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.services import pedido_status_reconciliation_service as service

    monkeypatch.setattr(
        service,
        "_RATE_LIMIT_DIARIO_BLOQUEADO_ATE",
        datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    monkeypatch.setattr(service, "_contar_pedidos_recentes_reconciliaveis", lambda *args, **kwargs: 12)

    result = service.reconciliar_status_pedidos_recentes(object(), "tenant-1", dias=3, limite_pedidos=5)

    assert result["correlation_id"].startswith("job.pedido-status-reconciliation-")
    assert result["motivo"] == "bling_rate_limit_diario_ativo"
    assert get_request_id() is None

