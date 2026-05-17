from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "check_dev_environment.ps1"


def _powershell_command() -> str:
    for candidate in ("pwsh", "powershell"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    pytest.skip("PowerShell nao esta disponivel neste ambiente")


def test_check_dev_environment_json_is_structured_and_redacts_secret_values():
    env = os.environ.copy()
    env["DATABASE_URL"] = "postgresql://user:super-secret-db-password@localhost/petshop"
    env["JWT_SECRET_KEY"] = "super-secret-jwt-key"
    env["SMTP_PASSWORD"] = "super-secret-smtp-password"

    completed = subprocess.run(
        [
            _powershell_command(),
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
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
    assert "super-secret-smtp-password" not in output

    report = json.loads(output)
    assert report["project"] == "Sistema-Pet"
    assert report["mode"] == "no-network"
    assert report["summary"]["total"] > 0
    assert report["summary"]["warnings"] >= 0
    assert isinstance(report["checks"], list)

    check_ids = {check["id"] for check in report["checks"]}
    assert {
        "tool.git",
        "tool.python",
        "tool.node",
        "tool.npm",
        "tool.docker",
        "tool.gh",
        "tool.ssh",
        "project.required_paths",
        "project.env_file",
        "git.working_tree",
        "network.github_auth",
        "ports.backend",
        "ports.frontend",
        "ports.postgres",
    }.issubset(check_ids)
