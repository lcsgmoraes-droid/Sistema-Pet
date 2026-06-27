from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def line_count(relative_path: str) -> int:
    return len(read(relative_path).splitlines())


def test_backend_large_files_700_batch_5_ops_dashboard_modules_stay_below_limit():
    target_files = [
        "app/services/ops_dashboard_service.py",
        "app/services/ops_dashboard_utils.py",
        "app/services/ops_dashboard_incidents.py",
        "app/services/ops_dashboard_actionable_alerts.py",
        "app/services/ops_dashboard_health.py",
        "app/services/ops_dashboard_period_alerts.py",
    ]

    for relative_path in target_files:
        path = ROOT / relative_path
        assert path.exists(), (
            f"Missing extracted backend refactor file: {relative_path}"
        )
        assert line_count(relative_path) <= 700, (
            f"{relative_path} has {line_count(relative_path)} lines; expected <= 700"
        )


def test_backend_large_files_700_batch_5_ops_dashboard_service_is_orchestrator():
    source = read("app/services/ops_dashboard_service.py")

    expected_imports = [
        "from app.services.ops_dashboard_actionable_alerts import _build_actionable_alerts",
        "from app.services.ops_dashboard_health import",
        "from app.services.ops_dashboard_incidents import",
        "from app.services.ops_dashboard_period_alerts import _build_alerts",
        "from app.services.ops_dashboard_utils import",
    ]

    for import_line in expected_imports:
        assert import_line in source

    assert "def build_ops_dashboard(" in source
    assert "def _build_actionable_alerts(" not in source
    assert "def _build_tenant_incidents(" not in source
    assert "def _watchdog_now(" not in source
    assert line_count("app/services/ops_dashboard_service.py") <= 220


def test_backend_large_files_700_batch_5_public_entrypoint_stays_available():
    from app.services.ops_dashboard_service import build_ops_dashboard

    assert callable(build_ops_dashboard)


def test_backend_large_files_700_batch_5_keeps_alert_helpers_in_focused_modules():
    actionable_alerts = read("app/services/ops_dashboard_actionable_alerts.py")
    period_alerts = read("app/services/ops_dashboard_period_alerts.py")
    health = read("app/services/ops_dashboard_health.py")

    assert "def _build_actionable_alerts(" in actionable_alerts
    assert "def _last_failed_deploy_after_success(" in actionable_alerts
    assert "def _build_alerts(" in period_alerts
    assert "def _current_health_status(" in health
