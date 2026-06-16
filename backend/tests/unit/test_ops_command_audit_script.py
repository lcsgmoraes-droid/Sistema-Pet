import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASH = Path("C:/Program Files/Git/bin/bash.exe")
SCRIPT = ROOT / "scripts" / "auditar_comando_producao.sh"


def _run_audited_command(
    tmp_path: Path, *args: str
) -> tuple[subprocess.CompletedProcess[str], Path]:
    log_path = tmp_path / "ops_command_events.jsonl"
    env = os.environ.copy()
    env["OPS_COMMAND_AUDIT_LOG_PATH"] = log_path.as_posix()
    env["OPS_COMMAND_AUDIT_APP_DIR"] = ROOT.as_posix()
    env["OPS_COMMAND_AUDIT_PYTHON"] = Path(sys.executable).as_posix()

    result = subprocess.run(
        [str(BASH), SCRIPT.as_posix(), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result, log_path


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_ops_command_audit_records_success_and_redacts_command_args(tmp_path):
    result, log_path = _run_audited_command(
        tmp_path,
        "--action",
        "manual.echo",
        "--reason",
        "pytest",
        "--label",
        "echo-redaction",
        "--",
        "echo",
        "token=super-secret",
        "password=123456",
        "ok",
    )

    assert result.returncode == 0, result.stderr

    events = _read_jsonl(log_path)
    assert [event["status"] for event in events] == ["started", "success"]
    assert len({event["operation_id"] for event in events}) == 1
    assert events[0]["action"] == "manual.echo"
    assert events[0]["reason"] == "pytest"
    assert events[0]["label"] == "echo-redaction"
    assert events[1]["exit_code"] == 0
    assert "super-secret" not in events[0]["command_redacted"]
    assert "123456" not in events[0]["command_redacted"]
    assert "token=***REDACTED***" in events[0]["command_redacted"]
    assert "password=***REDACTED***" in events[0]["command_redacted"]


def test_ops_command_audit_records_failed_exit_code(tmp_path):
    result, log_path = _run_audited_command(
        tmp_path,
        "--action",
        "manual.failure",
        "--reason",
        "pytest",
        "--label",
        "false-command",
        "--",
        "false",
    )

    assert result.returncode == 1

    events = _read_jsonl(log_path)
    assert [event["status"] for event in events] == ["started", "failed"]
    assert events[1]["exit_code"] == 1


def test_ops_command_audit_requires_reason_before_running(tmp_path):
    result, log_path = _run_audited_command(
        tmp_path,
        "--action",
        "manual.no_reason",
        "--",
        "echo",
        "should-not-run",
    )

    assert result.returncode != 0
    assert not log_path.exists()
    assert "reason" in result.stderr.lower()
