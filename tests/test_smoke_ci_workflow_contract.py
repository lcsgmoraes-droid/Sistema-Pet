from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SMOKE_CI_WORKFLOW = ROOT / ".github" / "workflows" / "smoke-ci.yml"
FRONTEND_PACKAGE_JSON = ROOT / "frontend" / "package.json"


def test_smoke_ci_runs_all_root_contract_tests():
    source = SMOKE_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "python -m pytest tests -q" in source
    assert "tests/**" in source
    assert (
        "tests/test_ci_smoke_script.py tests/test_smoke_golive_script.py" not in source
    )


def test_smoke_ci_blocks_frontend_core_lint_and_format():
    source = SMOKE_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Frontend core lint (blocking)" in source
    assert "npm run lint:core" in source
    assert "Frontend core format (blocking)" in source
    assert "npm run format:core:check" in source


def test_frontend_package_exposes_core_lint_and_format_scripts():
    package = json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))

    assert (
        package["scripts"]["lint:core"]
        == "eslint src/api src/hooks src/utils src/helpers scripts --max-warnings=0"
    )
    assert (
        package["scripts"]["format:core:check"]
        == "prettier --check src/api src/hooks src/utils src/helpers scripts"
    )
    assert "eslint-plugin-react-hooks" in package["devDependencies"]
