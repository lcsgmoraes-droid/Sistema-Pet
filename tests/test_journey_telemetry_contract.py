from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "backend" / "app" / "ops_models.py"
MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "zxe20260826a1_ops_journey_events.py"
)
REPORTER = ROOT / "backend" / "app" / "services" / "journey_event_reporter.py"
MIDDLEWARE = ROOT / "backend" / "app" / "middlewares" / "request_context.py"
OPS_ROUTES = ROOT / "backend" / "app" / "routes" / "error_events_routes.py"
OPS_DASHBOARD = ROOT / "backend" / "app" / "services" / "ops_dashboard_service.py"
IDEMPOTENCY = ROOT / "backend" / "app" / "idempotency.py"
FRONTEND_DASHBOARD = ROOT / "frontend" / "src" / "pages" / "OpsDashboard.jsx"
JOURNEY_PANEL = (
    ROOT / "frontend" / "src" / "pages" / "opsDashboard" / "JourneySloPanel.jsx"
)


def test_migration_creates_sanitized_journey_event_table_on_current_head():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "zxe20260826a1"' in source
    assert 'down_revision = "zxd20260826a1"' in source
    assert '"ops_journey_events"' in source
    for column in (
        "event_key",
        "journey",
        "outcome",
        "reason_code",
        "duration_ms",
        "tenant_id",
        "request_id",
        "operation_id",
        "path_template",
    ):
        assert f'"{column}"' in source


def test_model_has_aggregation_indexes_and_no_personal_payload_columns():
    source = MODEL.read_text(encoding="utf-8")
    model_source = source[source.index("class OpsJourneyEvent") :]

    for index_name in (
        "ix_ops_journey_events_journey_created",
        "ix_ops_journey_events_tenant_journey_created",
        "ix_ops_journey_events_outcome_created",
    ):
        assert index_name in model_source
    for forbidden in (
        "email = Column",
        "user_agent = Column",
        "client_ip = Column",
        "payload = Column",
        "message = Column",
        "entity_id = Column",
    ):
        assert forbidden not in model_source


def test_request_context_records_journey_events_without_touching_business_routes():
    middleware = MIDDLEWARE.read_text(encoding="utf-8")
    reporter = REPORTER.read_text(encoding="utf-8")

    assert "record_http_journey_event(" in middleware
    assert '"auth.login"' in reporter
    assert '"auth.tenant_selection"' in reporter
    assert '"sale.finalization"' in reporter
    assert '"/vendas/{venda_id}/finalizar"' in reporter
    assert "request.body" not in reporter
    assert "await request.json" not in reporter
    assert "X-Idempotency-Replayed" in IDEMPOTENCY.read_text(encoding="utf-8")


def test_ops_admin_exposes_list_summary_and_dashboard_aggregation():
    routes = OPS_ROUTES.read_text(encoding="utf-8")
    dashboard = OPS_DASHBOARD.read_text(encoding="utf-8")

    assert '@router.get("/journey-events")' in routes
    assert '@router.get("/journey-events/summary")' in routes
    assert '"journeys": journey_summary' in dashboard
    assert '"journeys": list(reversed(journey_events))[:10]' in dashboard


def test_ops_frontend_renders_journey_slo_panel_and_sample_rule():
    dashboard = FRONTEND_DASHBOARD.read_text(encoding="utf-8")
    panel = JOURNEY_PANEL.read_text(encoding="utf-8")

    assert 'import JourneySloPanel from "./opsDashboard/JourneySloPanel"' in dashboard
    assert "<JourneySloPanel journeys={dashboard?.journeys} />" in dashboard
    assert "Menos de 100 operações" in panel
    assert "expected_rejections" in panel
    assert "payload" not in panel.lower()


def test_retention_and_slo_docs_reference_the_new_telemetry():
    retention = (ROOT / "docs" / "RETENCAO_LOGS_AUDITORIA.md").read_text(
        encoding="utf-8"
    )
    slos = (ROOT / "docs" / "SLOS_INDICADORES_JORNADAS.md").read_text(encoding="utf-8")

    assert "`ops_journey_events`" in retention
    assert "`backend/logs/journey_events.jsonl`" in retention
    assert "`ops_journey_events` e JSONL sanitizado" in slos
    assert "Implementado para login, seleção" in slos
