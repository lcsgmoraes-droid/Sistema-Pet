#!/usr/bin/env python
"""
Smoke test autenticado para go-live.

Uso:
  $env:GOLIVE_BASE_URL="https://mlprohub.com.br"
  $env:GOLIVE_ERP_EMAIL="admin@..."
  $env:GOLIVE_ERP_PASSWORD="..."
  python scripts/smoke_golive.py

Opcional:
  GOLIVE_TEST_EMAIL / GOLIVE_TEST_PASSWORD para validar um segundo tenant.

O script faz apenas leituras e login/selecao de tenant. Nao cria venda,
produto ou cliente.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://mlprohub.com.br"
TIMEOUT_SECONDS = int(os.getenv("GOLIVE_TIMEOUT_SECONDS", "20"))
DEFAULT_USER_AGENT = os.getenv(
    "GOLIVE_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)


@dataclass
class CheckResult:
    name: str
    ok: bool
    status: int | None = None
    elapsed_ms: int | None = None
    detail: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


class SmokeClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        expected: set[int] | None = None,
    ) -> tuple[CheckResult, Any]:
        expected = expected or {200}
        url = f"{self.base_url}{path}"
        data = None
        request_headers = {
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "User-Agent": DEFAULT_USER_AGENT,
            **(headers or {}),
        }
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"

        started = time.perf_counter()
        try:
            with urlopen(Request(url, data=data, headers=request_headers, method=method), timeout=TIMEOUT_SECONDS) as resp:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                raw = resp.read().decode("utf-8", errors="replace")
                payload = _parse_json(raw)
                return (
                    CheckResult(
                        name=f"{method} {path}",
                        ok=resp.status in expected,
                        status=resp.status,
                        elapsed_ms=elapsed_ms,
                        detail="ok" if resp.status in expected else f"status inesperado: {resp.status}",
                    ),
                    payload,
                )
        except HTTPError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            raw = exc.read().decode("utf-8", errors="replace")
            payload = _parse_json(raw)
            detail = _error_detail(payload) or raw[:240] or exc.reason
            return (
                CheckResult(
                    name=f"{method} {path}",
                    ok=exc.code in expected,
                    status=exc.code,
                    elapsed_ms=elapsed_ms,
                    detail=detail,
                ),
                payload,
            )
        except (URLError, TimeoutError) as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return (
                CheckResult(
                    name=f"{method} {path}",
                    ok=False,
                    elapsed_ms=elapsed_ms,
                    detail=str(exc),
                ),
                None,
            )


def _parse_json(raw: str) -> Any:
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return raw


def _error_detail(payload: Any) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message")
        if isinstance(detail, (str, int, float)):
            return str(detail)
        if detail is not None:
            return json.dumps(detail, ensure_ascii=False)[:240]
    return ""


def _append(results: list[CheckResult], result: CheckResult, *, name: str | None = None, detail: str | None = None) -> None:
    if name:
        result.name = name
    if detail:
        result.detail = detail
    results.append(result)


def _query(path: str, params: dict[str, Any]) -> str:
    return f"{path}?{urlencode(params)}"


def run_erp_flow(
    client: SmokeClient,
    results: list[CheckResult],
    *,
    label: str,
    email: str,
    password: str,
) -> dict[str, Any] | None:
    login_result, login_payload = client.request(
        "POST",
        "/api/auth/login-multitenant",
        body={"email": email, "password": password},
    )
    _append(results, login_result, name=f"{label}: login ERP")
    if not login_result.ok or not isinstance(login_payload, dict):
        return None

    tenants = login_payload.get("tenants") or []
    token = login_payload.get("access_token")
    tenant_id = tenants[0].get("id") if tenants else None
    results.append(
        CheckResult(
            name=f"{label}: tenants disponiveis",
            ok=bool(token and tenant_id),
            detail=f"{len(tenants)} tenant(s)",
            payload={"tenant_id": tenant_id},
        )
    )
    if not token or not tenant_id:
        return None

    select_result, select_payload = client.request(
        "POST",
        "/api/auth/select-tenant",
        token=token,
        body={"tenant_id": tenant_id},
    )
    _append(results, select_result, name=f"{label}: selecionar tenant")
    if not select_result.ok or not isinstance(select_payload, dict):
        return None

    final_token = select_payload.get("access_token")
    if not final_token:
        results.append(CheckResult(name=f"{label}: token final", ok=False, detail="access_token ausente"))
        return None

    me_result, me_payload = client.request("GET", "/api/auth/me-multitenant", token=final_token)
    permissions = []
    if isinstance(me_payload, dict):
        permissions = me_payload.get("permissions") or []
    _append(
        results,
        me_result,
        name=f"{label}: usuario/tenant atual",
        detail=f"{len(permissions)} permissoes" if me_result.ok else me_result.detail,
    )

    for path, name, expected in [
        (_query("/api/produtos/", {"page": 1, "page_size": 1}), f"{label}: produtos", {200}),
        (_query("/api/produtos/vendaveis", {"page": 1, "page_size": 1, "contar_total": "false"}), f"{label}: produtos vendaveis PDV", {200}),
        (_query("/api/clientes/", {"skip": 0, "limit": 1}), f"{label}: clientes", {200}),
        ("/api/caixas/aberto", f"{label}: caixa aberto", {200, 404}),
        ("/api/lgpd/status", f"{label}: LGPD status", {200, 403}),
    ]:
        result, _ = client.request("GET", path, token=final_token, expected=expected)
        if result.status == 403 and "LGPD" in name:
            result.detail = "sem permissao LGPD neste perfil"
        _append(results, result, name=name)

    context_path = _query("/api/ecommerce/tenant-context", {"tenant": tenant_id})
    ctx_result, _ = client.request("GET", context_path)
    _append(results, ctx_result, name=f"{label}: ecommerce tenant-context")

    catalog_path = _query("/api/ecommerce/produtos", {"tenant": tenant_id, "limit": 1, "canal": "ecommerce"})
    catalog_result, _ = client.request("GET", catalog_path)
    _append(results, catalog_result, name=f"{label}: ecommerce catalogo publico")

    app_catalog_path = _query("/api/ecommerce/produtos", {"tenant": tenant_id, "limit": 1, "canal": "app"})
    app_catalog_result, _ = client.request("GET", app_catalog_path)
    _append(results, app_catalog_result, name=f"{label}: app catalogo publico")

    return {"tenant_id": tenant_id, "token": final_token}


def main() -> int:
    base_url = os.getenv("GOLIVE_BASE_URL", DEFAULT_BASE_URL)
    client = SmokeClient(base_url)
    results: list[CheckResult] = []

    for path, name in [
        ("/health", "health publico"),
        ("/login", "frontend login"),
        ("/termos", "frontend termos"),
        ("/privacidade", "frontend privacidade"),
        ("/verificar-email", "frontend verificar email"),
    ]:
        result, _ = client.request("GET", path, expected={200})
        _append(results, result, name=name)

    email = os.getenv("GOLIVE_ERP_EMAIL")
    password = os.getenv("GOLIVE_ERP_PASSWORD")
    if email and password:
        run_erp_flow(client, results, label="tenant principal", email=email, password=password)
    else:
        results.append(
            CheckResult(
                name="tenant principal: login ERP",
                ok=False,
                detail="defina GOLIVE_ERP_EMAIL e GOLIVE_ERP_PASSWORD",
            )
        )

    test_email = os.getenv("GOLIVE_TEST_EMAIL")
    test_password = os.getenv("GOLIVE_TEST_PASSWORD")
    if test_email and test_password:
        run_erp_flow(client, results, label="tenant teste", email=test_email, password=test_password)

    failed = [result for result in results if not result.ok]
    for result in results:
        marker = "OK" if result.ok else "FAIL"
        status = f" status={result.status}" if result.status is not None else ""
        timing = f" {result.elapsed_ms}ms" if result.elapsed_ms is not None else ""
        print(f"[{marker}] {result.name}{status}{timing} - {result.detail}")

    print()
    print(f"Resumo: {len(results) - len(failed)}/{len(results)} checks OK")
    if failed:
        print("Falhas:")
        for result in failed:
            print(f"- {result.name}: {result.detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
