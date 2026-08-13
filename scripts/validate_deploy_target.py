#!/usr/bin/env python3
"""Bloqueia deploy quando o host nao corresponde ao dominio publico do CorePet."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import ipaddress
import socket
import subprocess
from urllib.parse import urlparse


class DeployTargetError(RuntimeError):
    """Indica que o deploy foi iniciado no destino errado."""


@dataclass(frozen=True)
class DeployTargetResult:
    domain: str
    local_ips: set[str]
    resolved_ips: set[str]
    matched_ips: set[str]


def _normalize_ips(values: set[str]) -> set[str]:
    normalized: set[str] = set()
    for value in values:
        candidate = value.strip()
        if not candidate:
            continue
        try:
            normalized.add(str(ipaddress.ip_address(candidate)))
        except ValueError:
            continue
    return normalized


def resolve_domain_ips(domain: str) -> set[str]:
    try:
        records = socket.getaddrinfo(domain, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise DeployTargetError(
            f"Deploy bloqueado: nao foi possivel resolver o dominio {domain}: {exc}"
        ) from exc

    return _normalize_ips({record[4][0] for record in records})


def discover_local_ips() -> set[str]:
    try:
        result = subprocess.run(
            ["hostname", "-I"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DeployTargetError(
            f"Deploy bloqueado: nao foi possivel identificar os IPs deste servidor: {exc}"
        ) from exc

    return _normalize_ips(set(result.stdout.split()))


def validate_target(
    *,
    domain: str,
    local_ips: set[str],
    resolved_ips: set[str],
    health_url: str,
) -> DeployTargetResult:
    normalized_domain = domain.strip().lower().rstrip(".")
    health_host = (urlparse(health_url).hostname or "").lower().rstrip(".")
    allowed_health_hosts = {normalized_domain, f"www.{normalized_domain}"}
    if health_host not in allowed_health_hosts:
        raise DeployTargetError(
            "Deploy bloqueado: o health check deve usar o mesmo dominio publico "
            f"({normalized_domain}), mas recebeu {health_host or 'URL invalida'}."
        )

    normalized_local = _normalize_ips(local_ips)
    normalized_resolved = _normalize_ips(resolved_ips)
    if not normalized_local:
        raise DeployTargetError("Deploy bloqueado: este servidor nao informou nenhum IP local.")
    if not normalized_resolved:
        raise DeployTargetError(
            f"Deploy bloqueado: {normalized_domain} nao resolveu para nenhum IP."
        )

    matched = normalized_local & normalized_resolved
    if not matched:
        raise DeployTargetError(
            "Deploy bloqueado: servidor errado. "
            f"{normalized_domain} aponta para {', '.join(sorted(normalized_resolved))}, "
            f"mas este host possui {', '.join(sorted(normalized_local))}."
        )

    return DeployTargetResult(
        domain=normalized_domain,
        local_ips=normalized_local,
        resolved_ips=normalized_resolved,
        matched_ips=matched,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="corepet.com.br")
    parser.add_argument("--health-url", default="https://corepet.com.br/api/health")
    parser.add_argument("--local-ip", action="append", default=[])
    parser.add_argument("--resolved-ip", action="append", default=[])
    args = parser.parse_args()

    local_ips = set(args.local_ip) if args.local_ip else discover_local_ips()
    resolved_ips = set(args.resolved_ip) if args.resolved_ip else resolve_domain_ips(args.domain)

    try:
        result = validate_target(
            domain=args.domain,
            local_ips=local_ips,
            resolved_ips=resolved_ips,
            health_url=args.health_url,
        )
    except DeployTargetError as exc:
        parser.exit(1, f"{exc}\n")

    print(
        "Destino de producao confirmado: "
        f"{result.domain} -> {', '.join(sorted(result.matched_ips))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
