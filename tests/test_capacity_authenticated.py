from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capacity_authenticated.py"


def load_module():
    spec = importlib.util.spec_from_file_location("capacity_authenticated", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_base_url_allows_local_homologation_with_api_prefix():
    module = load_module()
    assert module.validate_base_url("http://127.0.0.1:18080/api/") == (
        "http://127.0.0.1:18080/api"
    )


def test_base_url_blocks_remote_without_explicit_flag():
    module = load_module()
    with pytest.raises(
        module.AuthenticatedCapacityError, match="Alvo remoto bloqueado"
    ):
        module.validate_base_url("https://staging.example.test/api")


def test_base_url_blocks_production_even_when_remote_is_allowed():
    module = load_module()
    with pytest.raises(
        module.AuthenticatedCapacityError,
        match="producao esta bloqueado",
    ):
        module.validate_base_url(
            "https://api.corepet.com.br/api",
            allow_remote=True,
        )


def test_authentication_selects_explicit_tenant_without_exposing_secret():
    module = load_module()
    calls = []

    def fake_requester(method, url, timeout, headers, payload):
        calls.append((method, url, timeout, headers, payload))
        if url.endswith("/auth/login-multitenant"):
            return (
                200,
                {
                    "access_token": "temporary-token",
                    "tenants": [{"id": "tenant-a"}],
                },
                12.5,
            )
        return 200, {"access_token": "final-token"}, 8.25

    token, timings = module.authenticate(
        base_url="http://127.0.0.1:18080/api",
        email="homologacao@corepet.test",
        password="secret-only-in-memory",
        tenant_id="tenant-a",
        timeout_seconds=5,
        requester=fake_requester,
    )

    assert token == "final-token"
    assert timings == {"login": 12.5, "tenant_selection": 8.25, "total": 20.75}
    assert calls[1][3]["Authorization"] == "Bearer temporary-token"
    assert calls[1][4] == {"tenant_id": "tenant-a"}


def test_authentication_rejects_tenant_not_returned_by_login():
    module = load_module()

    def fake_requester(_method, _url, _timeout, _headers, _payload):
        return (
            200,
            {
                "access_token": "temporary-token",
                "tenants": [{"id": "tenant-a"}],
            },
            10,
        )

    with pytest.raises(module.AuthenticatedCapacityError, match="nao pertence"):
        module.authenticate(
            base_url="http://127.0.0.1:18080/api",
            email="homologacao@corepet.test",
            password="secret-only-in-memory",
            tenant_id="tenant-b",
            timeout_seconds=5,
            requester=fake_requester,
        )


def test_read_only_route_catalog_has_no_mutating_method_or_free_form_path():
    module = load_module()
    assert [route.name for route in module.READ_ONLY_ROUTES] == [
        "auth.me",
        "customers.list",
        "products.list",
        "sales.list",
    ]
    assert all(route.path.startswith("/") for route in module.READ_ONLY_ROUTES)
    assert all(
        fragment not in route.path
        for route in module.READ_ONLY_ROUTES
        for fragment in ("/criar", "/finalizar", "/cancelar", "/excluir")
    )


def test_capacity_summary_passes_only_when_every_route_meets_criteria():
    module = load_module()

    def healthy_probe(_base_url, route, _token, _timeout):
        return module.ProbeResult(route.name, True, 200, 25.0)

    summary = module.run_authenticated_capacity(
        base_url="http://127.0.0.1:18080/api",
        token="token-in-memory",
        request_count=8,
        concurrency=4,
        timeout_seconds=5,
        min_success_rate=99.5,
        max_p95_ms=1500,
        authentication_ms={"total": 20},
        probe=healthy_probe,
    )

    assert summary.passed is True
    assert summary.success_rate == 100
    assert summary.authentication_ms == {"total": 20}
    assert len(summary.routes) == 4
    assert all(route.requests == 2 for route in summary.routes)
    assert all(route.status_counts == {"200": 2} for route in summary.routes)


def test_capacity_summary_fails_when_one_route_is_slow():
    module = load_module()

    def mixed_probe(_base_url, route, _token, _timeout):
        duration = 2000 if route.name == "sales.list" else 25
        return module.ProbeResult(route.name, True, 200, duration)

    summary = module.run_authenticated_capacity(
        base_url="http://127.0.0.1:18080/api",
        token="token-in-memory",
        request_count=8,
        concurrency=4,
        timeout_seconds=5,
        min_success_rate=99.5,
        max_p95_ms=1500,
        probe=mixed_probe,
    )

    assert summary.passed is False
    sales = next(route for route in summary.routes if route.route == "sales.list")
    assert sales.passed is False
    assert sales.latency_p95_ms == 2000


def test_capacity_limits_concurrency_and_request_volume():
    module = load_module()

    with pytest.raises(module.AuthenticatedCapacityError, match="Concorrencia"):
        module.run_authenticated_capacity(
            base_url="http://127.0.0.1:18080/api",
            token="token-in-memory",
            request_count=40,
            concurrency=21,
            timeout_seconds=5,
            min_success_rate=99.5,
            max_p95_ms=1500,
        )
