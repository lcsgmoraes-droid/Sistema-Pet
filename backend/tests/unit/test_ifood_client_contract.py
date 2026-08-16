from urllib.parse import parse_qs

import httpx
import pytest

from app.integrations.ifood.client import IfoodClient, IfoodClientError


def test_authenticates_once_and_never_uses_destructive_reset():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/authentication/v1.0/oauth/token":
            form = parse_qs(request.content.decode())
            assert form == {
                "grantType": ["client_credentials"],
                "clientId": ["corepet-client"],
                "clientSecret": ["server-secret"],
            }
            return httpx.Response(
                200,
                json={"accessToken": "safe-token", "expiresIn": 3600},
            )
        assert request.headers["Authorization"] == "Bearer safe-token"
        if request.url.path == "/merchant/v1.0/merchants":
            return httpx.Response(200, json=[{"id": "merchant-id"}])
        assert request.url.path == "/item/v1.0/ingestion/merchant-id"
        assert request.url.params.get("reset") == "false"
        return httpx.Response(202)

    client = IfoodClient(
        client_id="corepet-client",
        client_secret="server-secret",
        transport=httpx.MockTransport(handler),
    )
    with client:
        assert client.list_merchants() == [{"id": "merchant-id"}]
        result = client.ingest_items(
            "merchant-id",
            [{"barcode": "789", "name": "Produto"}],
            method="POST",
        )

    assert result == {"status_code": 202}
    assert (
        sum(
            request.url.path == "/authentication/v1.0/oauth/token"
            for request in requests
        )
        == 1
    )


def test_credential_failure_does_not_expose_client_secret():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "invalid secret-value"})

    client = IfoodClient(
        client_id="client",
        client_secret="secret-value",
        transport=httpx.MockTransport(handler),
    )
    with client, pytest.raises(IfoodClientError) as caught:
        client.list_merchants()

    assert "secret-value" not in str(caught.value)
    assert caught.value.status_code == 401


def test_patch_does_not_add_reset_parameter():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/authentication/v1.0/oauth/token":
            return httpx.Response(200, json={"accessToken": "token", "expiresIn": 3600})
        assert request.method == "PATCH"
        assert "reset" not in request.url.params
        return httpx.Response(202)

    client = IfoodClient(
        client_id="client",
        client_secret="secret",
        transport=httpx.MockTransport(handler),
    )
    with client:
        result = client.ingest_items(
            "merchant-id",
            [{"barcode": "789", "prices": {"price": 10}}],
            method="PATCH",
        )

    assert result["status_code"] == 202
