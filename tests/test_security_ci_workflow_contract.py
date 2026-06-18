from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SECURITY_CI_WORKFLOW = ROOT / ".github" / "workflows" / "security-ci.yml"
TRIVY_ACTION_SHA = "ed142fd0673e97e23eac54620cfb913e5ce36c25"


def _load_workflow() -> dict:
    assert SECURITY_CI_WORKFLOW.exists(), "Security CI workflow missing"
    return yaml.safe_load(SECURITY_CI_WORKFLOW.read_text(encoding="utf-8"))


def test_security_ci_runs_on_pull_request_push_and_schedule():
    workflow = _load_workflow()

    triggers = workflow[True]
    assert "pull_request" in triggers
    assert "push" in triggers
    assert "schedule" in triggers


def test_security_ci_has_blocking_codeql_job():
    workflow = _load_workflow()

    codeql_job = workflow["jobs"]["codeql"]
    step_sources = "\n".join(
        step.get("uses", "") or step.get("run", "") for step in codeql_job["steps"]
    )

    assert "github/codeql-action/init@v4" in step_sources
    assert "github/codeql-action/analyze@v4" in step_sources
    assert codeql_job["permissions"]["security-events"] == "write"


def test_security_ci_has_blocking_trivy_filesystem_scan():
    workflow = _load_workflow()

    trivy_job = workflow["jobs"]["trivy"]
    step_sources = "\n".join(
        step.get("uses", "") or step.get("run", "") for step in trivy_job["steps"]
    )

    assert f"aquasecurity/trivy-action@{TRIVY_ACTION_SHA}" in step_sources
    assert any(
        step.get("with", {}).get("scan-type") == "fs" for step in trivy_job["steps"]
    )
    assert any(
        step.get("with", {}).get("exit-code") == "1" for step in trivy_job["steps"]
    )
