from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_CI_WORKFLOW = ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_backend_ci_has_blocking_tenancy_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Tenancy lint (blocking)" in source
    assert "ruff check app/tenancy" in source


def test_backend_ci_has_blocking_auth_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Auth lint (blocking)" in source
    assert "ruff check app/auth app/auth_routes_multitenant.py app/usuarios_routes.py" in source


def test_backend_ci_has_blocking_db_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Database lint (blocking)" in source
    assert "ruff check app/db" in source


def test_backend_ci_has_blocking_schemas_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Schemas lint (blocking)" in source
    assert "ruff check app/schemas" in source


def test_backend_ci_has_blocking_security_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Security lint (blocking)" in source
    assert "ruff check app/security" in source


def test_backend_ci_has_blocking_core_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Core lint (blocking)" in source
    assert "ruff check app/core" in source


def test_backend_ci_has_blocking_events_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Events lint (blocking)" in source
    assert "ruff check app/events" in source


def test_backend_ci_has_blocking_utils_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Utils lint (blocking)" in source
    assert "ruff check app/utils" in source


def test_backend_ci_has_blocking_constants_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Constants lint (blocking)" in source
    assert "ruff check app/constants" in source


def test_backend_ci_has_blocking_cache_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Cache lint (blocking)" in source
    assert "ruff check app/cache" in source
