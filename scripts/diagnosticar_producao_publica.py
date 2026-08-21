from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_DOMAIN = "corepet.com.br"
DEFAULT_TIMEOUT_SECONDS = 10.0
RELEASE_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True)
class PublicCheck:
    name: str
    path: str
    kind: str


PUBLIC_CHECKS = (
    PublicCheck("API", "/api/health", "api_health"),
    PublicCheck("Watchdog", "/health/watchdog", "watchdog"),
    PublicCheck("Versao", "/release-commit.txt", "release"),
    PublicCheck("Rota web", "/notas-fiscais", "spa"),
)


def normalize_domain(domain: str) -> str:
    normalized = domain.strip().lower().rstrip(".")
    if (
        not normalized
        or "://" in normalized
        or "/" in normalized
        or not re.fullmatch(r"[a-z0-9.-]+", normalized)
    ):
        raise ValueError(
            "Dominio invalido. Informe apenas o host, sem https:// ou caminho."
        )
    return normalized


def validate_response(check: PublicCheck, status: int, content: str) -> str | None:
    if status != 200:
        return f"HTTP {status}"

    body = content.strip()
    if check.kind == "api_health":
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return "resposta da API nao e JSON valido"
        if payload.get("status") != "ok":
            return "API nao informou status ok"
    elif check.kind == "watchdog" and body.casefold() != "healthy":
        return "watchdog nao informou healthy"
    elif check.kind == "release" and not RELEASE_COMMIT_PATTERN.fullmatch(body):
        return "commit publico ausente ou invalido"
    elif check.kind == "spa" and "<html" not in body.casefold():
        return "rota web nao retornou o HTML da aplicacao"

    return None


def fetch_text(url: str, timeout: float) -> tuple[int, str]:
    request = Request(
        url,
        headers={"User-Agent": "Sistema-Pet-public-diagnostic/1.0"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise RuntimeError(f"falha de rede: {exc.reason}") from exc


def run_diagnostic(domain: str, timeout: float) -> int:
    base_url = f"https://{normalize_domain(domain)}"
    failures: list[str] = []

    print(f"Diagnostico publico somente leitura: {base_url}")
    for check in PUBLIC_CHECKS:
        url = f"{base_url}{check.path}"
        try:
            status, content = fetch_text(url, timeout)
            error = validate_response(check, status, content)
        except RuntimeError as exc:
            error = str(exc)
            content = ""

        if error:
            failures.append(f"{check.name}: {error}")
            print(f"FALHOU - {check.name}: {error}")
            continue

        detail = f" ({content.strip()[:12]})" if check.kind == "release" else ""
        print(f"OK - {check.name}{detail}")

    if failures:
        print("Diagnostico terminou com falhas; nenhuma alteracao foi executada.")
        return 1

    print("Producao publica saudavel; nenhuma alteracao foi executada.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consulta endpoints publicos sem alterar a producao."
    )
    parser.add_argument("--domain", default=DEFAULT_DOMAIN)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.timeout <= 0:
        print("Timeout deve ser maior que zero.", file=sys.stderr)
        return 2
    try:
        return run_diagnostic(args.domain, args.timeout)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
