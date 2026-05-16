from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SMOKE_GOLIVE_SCRIPT = ROOT / "scripts" / "smoke_golive.py"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("smoke_golive", SMOKE_GOLIVE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakePublicClient:
    calls: list[tuple[str, str]] = []
    result_class = None

    def __init__(self, base_url: str):
        self.base_url = base_url

    def request(self, method: str, path: str, **kwargs):
        self.calls.append((method, path))
        return self.result_class(name=f"{method} {path}", ok=True, status=200, detail="ok"), {}


def test_public_only_mode_skips_authenticated_login_without_credentials(monkeypatch, capsys):
    smoke = _load_smoke_module()
    FakePublicClient.calls = []
    FakePublicClient.result_class = smoke.CheckResult

    monkeypatch.setenv("GOLIVE_PUBLIC_ONLY", "true")
    monkeypatch.setenv("GOLIVE_BASE_URL", "https://example.test")
    monkeypatch.delenv("GOLIVE_ERP_EMAIL", raising=False)
    monkeypatch.delenv("GOLIVE_ERP_PASSWORD", raising=False)
    monkeypatch.setattr(smoke, "SmokeClient", FakePublicClient)

    exit_code = smoke.main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "tenant principal: login ERP" not in output
    assert ("POST", "/api/auth/login-multitenant") not in FakePublicClient.calls
    assert ("GET", "/health") in FakePublicClient.calls
