"""Resolve the real client IP without trusting public spoofed headers."""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Iterable

from fastapi import Request


DEFAULT_TRUSTED_PROXY_CIDRS = (
    "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
)


def _proxy_networks(cidrs: str | None = None) -> tuple:
    configured = cidrs or os.getenv("TRUSTED_PROXY_CIDRS", DEFAULT_TRUSTED_PROXY_CIDRS)
    return tuple(
        ipaddress.ip_network(value.strip(), strict=False)
        for value in configured.split(",")
        if value.strip()
    )


def is_trusted_proxy(peer_ip: str | None, *, cidrs: str | None = None) -> bool:
    if not peer_ip:
        return False
    try:
        address = ipaddress.ip_address(peer_ip)
    except ValueError:
        return False
    return any(address in network for network in _proxy_networks(cidrs))


def _first_valid_ip(values: Iterable[str | None]) -> str | None:
    for value in values:
        candidate = (value or "").split(",", 1)[0].strip()
        if not candidate:
            continue
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return None


def get_client_ip(request: Request | None) -> str | None:
    """Return proxy-provided IP only when the direct peer is trusted."""

    if not request or not request.client:
        return None

    peer_ip = request.client.host
    if is_trusted_proxy(peer_ip):
        forwarded_ip = _first_valid_ip(
            (
                request.headers.get("x-forwarded-for"),
                request.headers.get("x-real-ip"),
            )
        )
        if forwarded_ip:
            return forwarded_ip

    return _first_valid_ip((peer_ip,)) or peer_ip
