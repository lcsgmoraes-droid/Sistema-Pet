from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SMOKE_CI_WORKFLOW = ROOT / ".github" / "workflows" / "smoke-ci.yml"
DEPLOY_SAFETY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy-safety.yml"
FRONTEND_PACKAGE_JSON = ROOT / "frontend" / "package.json"


def test_smoke_ci_runs_all_root_contract_tests():
    source = SMOKE_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "python -m pytest tests -q" in source
    assert (
        "tests/test_ci_smoke_script.py tests/test_smoke_golive_script.py" not in source
    )


def test_required_main_checks_are_not_skipped_by_path_filters():
    smoke = SMOKE_CI_WORKFLOW.read_text(encoding="utf-8")
    deploy_safety = DEPLOY_SAFETY_WORKFLOW.read_text(encoding="utf-8")

    assert "paths:" not in smoke
    assert "paths:" not in deploy_safety
    assert "Smoke test" in smoke
    assert "Fluxo unico safety" in deploy_safety


def test_smoke_ci_blocks_frontend_core_lint_and_format():
    source = SMOKE_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Frontend core lint (blocking)" in source
    assert "npm run lint:core" in source
    assert "Frontend core format (blocking)" in source
    assert "npm run format:core:check" in source


def test_smoke_ci_blocks_frontend_dependency_audit():
    source = SMOKE_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Frontend dependency audit (blocking)" in source
    assert "npm audit --audit-level=moderate" in source


def test_frontend_package_exposes_core_lint_and_format_scripts():
    package = json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))

    assert (
        package["scripts"]["lint:core"]
        == 'eslint "src/**/*.{js,jsx,ts,tsx,mjs,cjs}" scripts --max-warnings=0'
    )
    assert (
        package["scripts"]["format:core:check"]
        == 'prettier --check "src/**/*.{js,jsx,ts,tsx,mjs,cjs,css,md}" scripts'
    )
    assert "eslint-plugin-react-hooks" in package["devDependencies"]
