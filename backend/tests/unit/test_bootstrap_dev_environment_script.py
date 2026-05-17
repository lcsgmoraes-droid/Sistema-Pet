from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "bootstrap_dev_environment.ps1"


def _powershell_command() -> str:
    for candidate in ("pwsh", "powershell"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    pytest.skip("PowerShell nao esta disponivel neste ambiente")


def test_bootstrap_dev_environment_dry_run_lists_safe_idempotent_steps():
    env = os.environ.copy()
    env["DATABASE_URL"] = "postgresql://user:super-secret-db-password@localhost/petshop"
    env["JWT_SECRET_KEY"] = "super-secret-jwt-key"

    completed = subprocess.run(
        [
            _powershell_command(),
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-DryRun",
            "-Json",
            "-NoNetwork",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout

    output = completed.stdout
    assert "super-secret-db-password" not in output
    assert "super-secret-jwt-key" not in output

    report = json.loads(output)
    assert report["project"] == "Sistema-Pet"
    assert report["mode"] == "dry-run"
    assert report["summary"]["total"] >= 5

    step_ids = {step["id"] for step in report["steps"]}
    assert {
        "check.dev_environment",
        "backend.venv",
        "backend.dependencies",
        "frontend.dependencies",
        "mcp.setup",
    }.issubset(step_ids)

    for step in report["steps"]:
        assert step["status"] in {"planned", "skipped", "ok"}
        assert "secret" not in step.get("command", "").lower()


def test_bootstrap_dev_environment_no_network_json_runs_check_without_extra_output():
    completed = subprocess.run(
        [
            _powershell_command(),
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-Json",
            "-NoNetwork",
            "-SkipBackend",
            "-SkipFrontend",
            "-SkipMcp",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "-NoNetwork nao encontrado" not in completed.stdout

    report = json.loads(completed.stdout)
    steps_by_id = {step["id"]: step for step in report["steps"]}
    assert steps_by_id["check.dev_environment"]["status"] == "ok"
    assert report["summary"]["total"] == 5
