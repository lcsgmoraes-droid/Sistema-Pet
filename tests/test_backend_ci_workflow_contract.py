from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_CI_WORKFLOW = ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_backend_ci_has_blocking_tenancy_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Tenancy lint (blocking)" in source
    assert "ruff check app/tenancy" in source
