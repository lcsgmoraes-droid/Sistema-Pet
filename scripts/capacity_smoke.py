from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import json
import math
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
READ_ONLY_PATHS = {"/health", "/api/health", "/health/watchdog"}


class CapacitySmokeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    status_code: int
    duration_ms: float
    error: str | None = None


@dataclass(frozen=True)
class CapacitySummary:
    target: str
    requests: int
    concurrency: int
    successes: int
    failures: int
    success_rate: float
    elapsed_seconds: float
    requests_per_second: float
    latency_min_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_max_ms: float
    passed: bool
    criteria: dict[str, float]


def build_target(base_url: str, path: str, *, allow_production: bool = False) -> str:
    normalized_path = f"/{str(path or '').strip().lstrip('/')}"
    if normalized_path not in READ_ONLY_PATHS:
        allowed = ", ".join(sorted(READ_ONLY_PATHS))
        raise CapacitySmokeError(
            f"Endpoint nao permitido. Use apenas endpoints de leitura: {allowed}."
        )

    parsed = urlparse(str(base_url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CapacitySmokeError("Base URL invalida. Use http:// ou https://.")
    is_local = parsed.hostname.lower() in LOCAL_HOSTS
    if not is_local and not allow_production:
        raise CapacitySmokeError(
            "Alvo remoto bloqueado. Rode localmente ou informe --allow-production "
            "somente apos autorizacao explicita."
        )
    if not is_local and parsed.scheme != "https":
        raise CapacitySmokeError("Alvo remoto exige HTTPS.")
    return urljoin(f"{parsed.scheme}://{parsed.netloc}", normalized_path)


def _request_once(target: str, timeout_seconds: float) -> ProbeResult:
    started = time.perf_counter()
    request = Request(
        target,
        method="GET",
        headers={
            "User-Agent": "CorePet-Capacity-Smoke/1.0",
            "Accept": "application/json",
        },
    )
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
    duration_ms = (time.perf_counter() - started) * 1000
    return ProbeResult(
        ok=200 <= status_code < 300,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
        error=error,
    )


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    rank = max(math.ceil((percentile_value / 100) * len(ordered)) - 1, 0)
    return round(ordered[min(rank, len(ordered) - 1)], 2)


def run_capacity_smoke(
    *,
    target: str,
    request_count: int,
    concurrency: int,
    timeout_seconds: float,
    min_success_rate: float,
    max_p95_ms: float,
    probe: Callable[[str, float], ProbeResult] = _request_once,
) -> CapacitySummary:
    if not 1 <= request_count <= 5000:
        raise CapacitySmokeError("Quantidade de requisicoes deve ficar entre 1 e 5000.")
    if not 1 <= concurrency <= 50:
        raise CapacitySmokeError("Concorrencia deve ficar entre 1 e 50.")
    if concurrency > request_count:
        raise CapacitySmokeError(
            "Concorrencia nao pode superar o total de requisicoes."
        )

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(probe, target, timeout_seconds)
            for _ in range(request_count)
        ]
        results = [future.result() for future in as_completed(futures)]
    elapsed = max(time.perf_counter() - started, 0.000001)

    successes = sum(1 for result in results if result.ok)
    failures = request_count - successes
    success_rate = round((successes / request_count) * 100, 2)
    latencies = [result.duration_ms for result in results]
    p95 = percentile(latencies, 95)
    passed = success_rate >= min_success_rate and p95 <= max_p95_ms
    return CapacitySummary(
        target=target,
        requests=request_count,
        concurrency=concurrency,
        successes=successes,
        failures=failures,
        success_rate=success_rate,
        elapsed_seconds=round(elapsed, 2),
        requests_per_second=round(request_count / elapsed, 2),
        latency_min_ms=round(min(latencies), 2),
        latency_p50_ms=percentile(latencies, 50),
        latency_p95_ms=p95,
        latency_p99_ms=percentile(latencies, 99),
        latency_max_ms=round(max(latencies), 2),
        passed=passed,
        criteria={
            "min_success_rate": min_success_rate,
            "max_p95_ms": max_p95_ms,
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke de capacidade seguro e somente leitura do CorePet."
    )
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--path", default="/health", choices=sorted(READ_ONLY_PATHS))
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--min-success-rate", type=float, default=99.0)
    parser.add_argument("--max-p95-ms", type=float, default=500.0)
    parser.add_argument("--allow-production", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        target = build_target(
            args.base_url,
            args.path,
            allow_production=bool(args.allow_production),
        )
        summary = run_capacity_smoke(
            target=target,
            request_count=args.requests,
            concurrency=args.concurrency,
            timeout_seconds=args.timeout,
            min_success_rate=args.min_success_rate,
            max_p95_ms=args.max_p95_ms,
        )
    except CapacitySmokeError as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0 if summary.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
