import importlib.util
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "validate_release_gate.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("validate_release_gate", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_release_gate_requires_every_named_check_to_pass():
    module = _load_script()
    required = ("Quality Gate", "Smoke test")
    payload = {
        "check_runs": [
            {
                "name": "Quality Gate",
                "status": "completed",
                "conclusion": "success",
            },
            {
                "name": "Smoke test",
                "status": "completed",
                "conclusion": "failure",
            },
        ]
    }

    status, checks = module.evaluate_checks(payload, required)

    assert status == "failed"
    assert checks[1]["conclusion"] == "failure"


def test_release_gate_reports_missing_check_as_failure():
    module = _load_script()

    status, checks = module.evaluate_checks({"check_runs": []}, ("Quality Gate",))

    assert status == "failed"
    assert checks == [{"name": "Quality Gate", "status": "missing", "conclusion": None}]


def test_release_gate_uses_newest_rerun_for_same_check_name():
    module = _load_script()
    payload = {
        "check_runs": [
            {
                "id": 20,
                "name": "Quality Gate",
                "status": "completed",
                "conclusion": "success",
            },
            {
                "id": 10,
                "name": "Quality Gate",
                "status": "completed",
                "conclusion": "failure",
            },
        ]
    }

    status, checks = module.evaluate_checks(payload, ("Quality Gate",))

    assert status == "passed"
    assert checks[0]["conclusion"] == "success"


def test_release_gate_writes_evidence_atomically_with_safe_permissions(tmp_path):
    module = _load_script()
    path = tmp_path / "release_status.json.next"

    module.write_evidence(path, {"status": "passed"})

    assert path.read_text(encoding="utf-8") == '{"status":"passed"}\n'
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o644
