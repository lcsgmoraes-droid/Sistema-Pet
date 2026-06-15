from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SMOKE_CI_WORKFLOW = ROOT / ".github" / "workflows" / "smoke-ci.yml"


def test_smoke_ci_runs_all_root_contract_tests():
    source = SMOKE_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "python -m pytest tests -q" in source
    assert "tests/**" in source
    assert "tests/test_ci_smoke_script.py tests/test_smoke_golive_script.py" not in source
