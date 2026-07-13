from types import SimpleNamespace

from starlette.datastructures import Headers

from app.security.client_ip import get_client_ip, is_trusted_proxy


def _request(peer_ip: str, **headers: str):
    return SimpleNamespace(
        client=SimpleNamespace(host=peer_ip),
        headers=Headers(headers),
    )


def test_public_peer_cannot_spoof_forwarded_ip():
    request = _request(
        "203.0.113.10",
        **{"x-forwarded-for": "198.51.100.20", "x-real-ip": "198.51.100.21"},
    )

    assert get_client_ip(request) == "203.0.113.10"


def test_private_proxy_can_forward_valid_client_ip():
    request = _request("172.20.0.5", **{"x-forwarded-for": "198.51.100.20"})

    assert get_client_ip(request) == "198.51.100.20"


def test_invalid_forwarded_ip_falls_back_to_real_ip_then_peer():
    request = _request(
        "172.20.0.5",
        **{"x-forwarded-for": "not-an-ip", "x-real-ip": "198.51.100.21"},
    )

    assert get_client_ip(request) == "198.51.100.21"


def test_trusted_proxy_ranges_can_be_explicitly_restricted():
    assert is_trusted_proxy("10.0.0.8", cidrs="10.0.0.0/8") is True
    assert is_trusted_proxy("172.20.0.5", cidrs="10.0.0.0/8") is False
