from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT = ROOT / "scripts" / "ci_smoke.py"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("ci_smoke", SMOKE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeRoute:
    def __init__(self, path: str, methods: set[str]):
        self.path = path
        self.methods = methods


class FakeApp:
    routes = [
        FakeRoute("/health", {"GET"}),
        FakeRoute("/auth/login-multitenant", {"POST"}),
    ]


def test_assert_route_exists_accepts_registered_method():
    smoke = _load_smoke_module()

    smoke.assert_route_exists(FakeApp(), "/auth/login-multitenant", "POST")


def test_assert_route_exists_rejects_missing_method():
    smoke = _load_smoke_module()

    with pytest.raises(AssertionError, match="POST /health"):
        smoke.assert_route_exists(FakeApp(), "/health", "POST")
