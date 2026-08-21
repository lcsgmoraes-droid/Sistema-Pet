from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "diagnosticar_producao_publica.py"


def load_diagnostic():
    spec = importlib.util.spec_from_file_location(
        "diagnosticar_producao_publica", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def check_by_kind(module, kind: str):
    return next(check for check in module.PUBLIC_CHECKS if check.kind == kind)


def test_expected_public_responses_are_accepted():
    module = load_diagnostic()

    assert (
        module.validate_response(
            check_by_kind(module, "api_health"), 200, '{"status":"ok"}'
        )
        is None
    )
    assert (
        module.validate_response(check_by_kind(module, "watchdog"), 200, "healthy")
        is None
    )
    assert (
        module.validate_response(check_by_kind(module, "release"), 200, "a" * 40)
        is None
    )
    assert (
        module.validate_response(
            check_by_kind(module, "spa"), 200, "<!doctype html><html></html>"
        )
        is None
    )


def test_unhealthy_or_unexpected_responses_are_rejected():
    module = load_diagnostic()

    assert (
        module.validate_response(
            check_by_kind(module, "api_health"), 503, "unavailable"
        )
        == "HTTP 503"
    )
    assert (
        module.validate_response(check_by_kind(module, "watchdog"), 200, "degraded")
        == "watchdog nao informou healthy"
    )
    assert (
        module.validate_response(check_by_kind(module, "release"), 200, "unknown")
        == "commit publico ausente ou invalido"
    )
    assert (
        module.validate_response(
            check_by_kind(module, "spa"), 200, '{"detail":"not found"}'
        )
        == "rota web nao retornou o HTML da aplicacao"
    )


def test_domain_accepts_host_and_rejects_url_or_path():
    module = load_diagnostic()

    assert module.normalize_domain("COREPET.COM.BR.") == "corepet.com.br"
    with pytest.raises(ValueError):
        module.normalize_domain("https://corepet.com.br")
    with pytest.raises(ValueError):
        module.normalize_domain("corepet.com.br/api")
