from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capacity_smoke.py"


def load_module():
    spec = importlib.util.spec_from_file_location("capacity_smoke", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_target_allows_local_read_only_endpoint():
    module = load_module()
    assert module.build_target("http://localhost:8000", "/health") == (
        "http://localhost:8000/health"
    )


def test_build_target_blocks_remote_without_explicit_flag():
    module = load_module()
    with pytest.raises(module.CapacitySmokeError, match="Alvo remoto bloqueado"):
        module.build_target("https://corepet.com.br", "/api/health")


def test_build_target_blocks_mutating_or_unknown_path():
    module = load_module()
    with pytest.raises(module.CapacitySmokeError, match="Endpoint nao permitido"):
        module.build_target("http://localhost:8000", "/auth/login")


def test_percentile_uses_nearest_rank():
    module = load_module()
    assert module.percentile([10, 20, 30, 40, 50], 50) == 30
    assert module.percentile([10, 20, 30, 40, 50], 95) == 50


def test_capacity_summary_passes_with_healthy_samples():
    module = load_module()
    durations = iter([10, 20, 30, 40])

    def fake_probe(_target, _timeout):
        return module.ProbeResult(True, 200, next(durations))

    result = module.run_capacity_smoke(
        target="http://localhost:8000/health",
        request_count=4,
        concurrency=2,
        timeout_seconds=1,
        min_success_rate=99,
        max_p95_ms=100,
        probe=fake_probe,
    )

    assert result.passed is True
    assert result.success_rate == 100
    assert result.latency_p50_ms == 20
    assert result.latency_p95_ms == 40


def test_capacity_summary_fails_when_success_rate_is_low():
    module = load_module()
    samples = iter([True, True, True, False])

    def fake_probe(_target, _timeout):
        ok = next(samples)
        return module.ProbeResult(ok, 200 if ok else 500, 20)

    result = module.run_capacity_smoke(
        target="http://localhost:8000/health",
        request_count=4,
        concurrency=2,
        timeout_seconds=1,
        min_success_rate=99,
        max_p95_ms=100,
        probe=fake_probe,
    )

    assert result.passed is False
    assert result.success_rate == 75
