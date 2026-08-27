from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import json
import math
import os
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
PRODUCTION_DOMAINS = {"corepet.com.br", "mlprohub.com.br"}
MAX_RESPONSE_BYTES = 65_536


class AuthenticatedCapacityError(RuntimeError):
    pass


@dataclass(frozen=True)
class RouteSpec:
    name: str
    path: str


READ_ONLY_ROUTES = (
    RouteSpec("auth.me", "/auth/me-multitenant"),
    RouteSpec("customers.list", "/clientes/?skip=0&limit=20"),
    RouteSpec("products.list", "/produtos/?page=1&page_size=20"),
    RouteSpec("sales.list", "/vendas?page=1&per_page=20"),
)


@dataclass(frozen=True)
class ProbeResult:
    route: str
    ok: bool
    status_code: int
    duration_ms: float
    error: str | None = None


@dataclass(frozen=True)
class RouteSummary:
    route: str
    requests: int
    successes: int
    failures: int
    success_rate: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_max_ms: float
    status_counts: dict[str, int]
    passed: bool


@dataclass(frozen=True)
class AuthenticatedCapacitySummary:
    base_url: str
    requests: int
    concurrency: int
    successes: int
    failures: int
    success_rate: float
    elapsed_seconds: float
    requests_per_second: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_max_ms: float
    authentication_ms: dict[str, float]
    sample_quality: str
    routes: list[RouteSummary]
    criteria: dict[str, float]
    passed: bool


JsonRequester = Callable[
    [str, str, float, dict[str, str], dict[str, str] | None],
    tuple[int, dict, float],
]
Probe = Callable[[str, RouteSpec, str, float], ProbeResult]


def _is_production_host(hostname: str) -> bool:
    normalized = hostname.strip().lower()
    return any(
        normalized == domain or normalized.endswith(f".{domain}")
        for domain in PRODUCTION_DOMAINS
    )


def validate_base_url(base_url: str, *, allow_remote: bool = False) -> str:
    value = str(base_url or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise AuthenticatedCapacityError("Base URL invalida. Use http:// ou https://.")
    if parsed.username or parsed.password:
        raise AuthenticatedCapacityError("Credenciais nao podem fazer parte da URL.")
    if parsed.query or parsed.fragment:
        raise AuthenticatedCapacityError("Base URL nao pode conter query ou fragmento.")

    hostname = parsed.hostname.lower()
    if _is_production_host(hostname):
        raise AuthenticatedCapacityError(
            "Teste autenticado de carga em producao esta bloqueado. Use homologacao."
        )

    is_local = hostname in LOCAL_HOSTS
    if not is_local and not allow_remote:
        raise AuthenticatedCapacityError(
            "Alvo remoto bloqueado. Use homologacao local ou --allow-remote para um "
            "staging isolado."
        )
    if not is_local and parsed.scheme != "https":
        raise AuthenticatedCapacityError("Staging remoto exige HTTPS.")
    return value


def endpoint_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    rank = max(math.ceil((percentile_value / 100) * len(ordered)) - 1, 0)
    return round(ordered[min(rank, len(ordered) - 1)], 2)


def _request_json(
    method: str,
    url: str,
    timeout_seconds: float,
    headers: dict[str, str],
    payload: dict[str, str] | None,
) -> tuple[int, dict, float]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=body, method=method, headers=headers)
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(MAX_RESPONSE_BYTES)
            status_code = int(response.status)
    except HTTPError as exc:
        status_code = int(exc.code)
        raw = b"{}"
    except (URLError, TimeoutError, OSError) as exc:
        raise AuthenticatedCapacityError(
            f"Falha de transporte durante autenticacao: {type(exc).__name__}."
        ) from exc

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    try:
        response_payload = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        response_payload = {}
    return status_code, response_payload, duration_ms


def authenticate(
    *,
    base_url: str,
    email: str,
    password: str,
    tenant_id: str,
    timeout_seconds: float,
    requester: JsonRequester = _request_json,
) -> tuple[str, dict[str, float]]:
    if not email.strip() or not password or not tenant_id.strip():
        raise AuthenticatedCapacityError(
            "Credenciais ausentes. Configure CAPACITY_USER_EMAIL, "
            "CAPACITY_USER_PASSWORD e CAPACITY_TENANT_ID."
        )

    common_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "CorePet-Authenticated-Capacity/1.0",
    }
    login_status, login_payload, login_ms = requester(
        "POST",
        endpoint_url(base_url, "/auth/login-multitenant"),
        timeout_seconds,
        common_headers,
        {"email": email.strip().lower(), "password": password},
    )
    if not 200 <= login_status < 300:
        raise AuthenticatedCapacityError(
            f"Falha na etapa auth.login (HTTP {login_status})."
        )

    temporary_token = str(login_payload.get("access_token") or "")
    available_tenants = {
        str(item.get("id"))
        for item in (login_payload.get("tenants") or [])
        if isinstance(item, dict) and item.get("id")
    }
    if not temporary_token:
        raise AuthenticatedCapacityError("Login nao retornou token temporario.")
    if tenant_id not in available_tenants:
        raise AuthenticatedCapacityError(
            "O tenant informado nao pertence ao usuario de homologacao."
        )

    select_headers = {
        **common_headers,
        "Authorization": f"Bearer {temporary_token}",
    }
    select_status, select_payload, select_ms = requester(
        "POST",
        endpoint_url(base_url, "/auth/select-tenant"),
        timeout_seconds,
        select_headers,
        {"tenant_id": tenant_id},
    )
    if not 200 <= select_status < 300:
        raise AuthenticatedCapacityError(
            f"Falha na etapa auth.tenant_selection (HTTP {select_status})."
        )

    final_token = str(select_payload.get("access_token") or "")
    if not final_token:
        raise AuthenticatedCapacityError("Selecao de tenant nao retornou token final.")
    return final_token, {
        "login": login_ms,
        "tenant_selection": select_ms,
        "total": round(login_ms + select_ms, 2),
    }


def _probe_once(
    base_url: str,
    route: RouteSpec,
    token: str,
    timeout_seconds: float,
) -> ProbeResult:
    request = Request(
        endpoint_url(base_url, route.path),
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "CorePet-Authenticated-Capacity/1.0",
            "X-Request-ID": f"capacity-{uuid4().hex[:16]}",
        },
    )
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response.read(256)
            status_code = int(response.status)
        error = None
    except HTTPError as exc:
        status_code = int(exc.code)
        error = f"HTTP {status_code}"
    except (URLError, TimeoutError, OSError) as exc:
        status_code = 0
        error = type(exc).__name__
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    return ProbeResult(
        route=route.name,
        ok=200 <= status_code < 300,
        status_code=status_code,
        duration_ms=duration_ms,
        error=error,
    )


def validate_warmup(
    *,
    base_url: str,
    token: str,
    timeout_seconds: float,
    probe: Probe = _probe_once,
) -> None:
    for route in READ_ONLY_ROUTES:
        result = probe(base_url, route, token, timeout_seconds)
        if not result.ok:
            raise AuthenticatedCapacityError(
                f"Warm-up falhou em {route.name} (HTTP {result.status_code})."
            )


def _summarize_route(
    route: str,
    results: list[ProbeResult],
    *,
    min_success_rate: float,
    max_p95_ms: float,
) -> RouteSummary:
    successes = sum(1 for result in results if result.ok)
    total = len(results)
    latencies = [result.duration_ms for result in results]
    success_rate = round((successes / total) * 100, 2)
    p95 = percentile(latencies, 95)
    status_counts: dict[str, int] = {}
    for result in results:
        key = str(result.status_code) if result.status_code else (result.error or "error")
        status_counts[key] = status_counts.get(key, 0) + 1
    return RouteSummary(
        route=route,
        requests=total,
        successes=successes,
        failures=total - successes,
        success_rate=success_rate,
        latency_p50_ms=percentile(latencies, 50),
        latency_p95_ms=p95,
        latency_p99_ms=percentile(latencies, 99),
        latency_max_ms=round(max(latencies), 2),
        status_counts=status_counts,
        passed=success_rate >= min_success_rate and p95 <= max_p95_ms,
    )


def run_authenticated_capacity(
    *,
    base_url: str,
    token: str,
    request_count: int,
    concurrency: int,
    timeout_seconds: float,
    min_success_rate: float,
    max_p95_ms: float,
    authentication_ms: dict[str, float] | None = None,
    probe: Probe = _probe_once,
) -> AuthenticatedCapacitySummary:
    if not len(READ_ONLY_ROUTES) <= request_count <= 2000:
        raise AuthenticatedCapacityError(
            f"Quantidade de requisicoes deve ficar entre {len(READ_ONLY_ROUTES)} e 2000."
        )
    if not 1 <= concurrency <= 20:
        raise AuthenticatedCapacityError("Concorrencia deve ficar entre 1 e 20.")
    if concurrency > request_count:
        raise AuthenticatedCapacityError(
            "Concorrencia nao pode superar o total de requisicoes."
        )
    if not 0 <= min_success_rate <= 100:
        raise AuthenticatedCapacityError("Taxa minima de sucesso deve ficar entre 0 e 100.")
    if max_p95_ms <= 0:
        raise AuthenticatedCapacityError("Limite de p95 deve ser positivo.")

    workload = [READ_ONLY_ROUTES[index % len(READ_ONLY_ROUTES)] for index in range(request_count)]
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(probe, base_url, route, token, timeout_seconds)
            for route in workload
        ]
        results = [future.result() for future in as_completed(futures)]
    elapsed = max(time.perf_counter() - started, 0.000001)

    successes = sum(1 for result in results if result.ok)
    latencies = [result.duration_ms for result in results]
    route_summaries = [
        _summarize_route(
            route.name,
            [result for result in results if result.route == route.name],
            min_success_rate=min_success_rate,
            max_p95_ms=max_p95_ms,
        )
        for route in READ_ONLY_ROUTES
    ]
    success_rate = round((successes / request_count) * 100, 2)
    p95 = percentile(latencies, 95)
    minimum_route_samples = min(item.requests for item in route_summaries)
    passed = (
        success_rate >= min_success_rate
        and p95 <= max_p95_ms
        and all(item.passed for item in route_summaries)
    )
    return AuthenticatedCapacitySummary(
        base_url=base_url,
        requests=request_count,
        concurrency=concurrency,
        successes=successes,
        failures=request_count - successes,
        success_rate=success_rate,
        elapsed_seconds=round(elapsed, 2),
        requests_per_second=round(request_count / elapsed, 2),
        latency_p50_ms=percentile(latencies, 50),
        latency_p95_ms=p95,
        latency_p99_ms=percentile(latencies, 99),
        latency_max_ms=round(max(latencies), 2),
        authentication_ms=authentication_ms or {},
        sample_quality=(
            "adequate_per_route" if minimum_route_samples >= 100 else "baseline_low_sample"
        ),
        routes=route_summaries,
        criteria={
            "min_success_rate": min_success_rate,
            "max_p95_ms": max_p95_ms,
        },
        passed=passed,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capacidade autenticada e somente leitura do CorePet em homologacao."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("CAPACITY_BASE_URL", "http://127.0.0.1:18080/api"),
    )
    parser.add_argument("--requests", type=int, default=320)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--min-success-rate", type=float, default=99.5)
    parser.add_argument("--max-p95-ms", type=float, default=1500.0)
    parser.add_argument("--allow-remote", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        base_url = validate_base_url(args.base_url, allow_remote=args.allow_remote)
        token, authentication_ms = authenticate(
            base_url=base_url,
            email=os.getenv("CAPACITY_USER_EMAIL", ""),
            password=os.getenv("CAPACITY_USER_PASSWORD", ""),
            tenant_id=os.getenv("CAPACITY_TENANT_ID", ""),
            timeout_seconds=args.timeout,
        )
        validate_warmup(
            base_url=base_url,
            token=token,
            timeout_seconds=args.timeout,
        )
        summary = run_authenticated_capacity(
            base_url=base_url,
            token=token,
            request_count=args.requests,
            concurrency=args.concurrency,
            timeout_seconds=args.timeout,
            min_success_rate=args.min_success_rate,
            max_p95_ms=args.max_p95_ms,
            authentication_ms=authentication_ms,
        )
    except AuthenticatedCapacityError as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0 if summary.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
