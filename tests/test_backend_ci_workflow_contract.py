from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_CI_WORKFLOW = ROOT / ".github" / "workflows" / "backend-ci.yml"


def _workflow_source() -> str:
    return BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")


def test_backend_ci_keeps_required_pr_guardrails():
    source = _workflow_source()

    assert "pull_request:" in source
    assert "branches: [main, develop]" in source
    assert "Python dependency audit (blocking)" in source
    assert (
        "pip-audit -r requirements.lock -s osv --progress-spinner off --timeout 60"
        in source
    )
    assert "Backend global lint (blocking)" in source
    assert "ruff check ." in source
    assert "Backend global format (blocking)" in source
    assert "ruff format --check ." in source


def test_backend_ci_keeps_multitenant_runtime_safety_suite():
    source = _workflow_source()

    assert "Multitenant hardening suite" in source
    assert (
        "pytest tests/multi_tenant -q --cov=app --cov-report=term --cov-report=xml"
        in source
    )
    assert "Import smoke test" in source
    assert "python -c \"import app.main; print('main import ok')\"" in source
    assert "Coverage report (informational)" in source


def test_backend_ci_keeps_postgres_migration_smoke():
    source = _workflow_source()

    assert "migration-smoke:" in source
    assert "image: postgres:16" in source
    assert "Run Alembic migration smoke" in source
    assert "python scripts/ci_migration_smoke.py" in source


def test_backend_ci_quality_gate_mirrors_sonarcloud_external_check():
    source = _workflow_source()

    assert "Quality Gate" in source
    assert "Ensure SonarCloud external check passed" in source
    assert "SonarCloud Code Analysis" in source
    assert "check-runs" in source
    assert "SONAR_WAIT_SECONDS" in source
