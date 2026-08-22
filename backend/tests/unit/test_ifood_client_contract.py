from urllib.parse import parse_qs
import json

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


def test_order_and_event_endpoints_follow_ifood_contracts():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path == "/authentication/v1.0/oauth/token":
            return httpx.Response(200, json={"accessToken": "token", "expiresIn": 3600})
        if path == "/events/v1.0/events:polling":
            assert request.headers["x-polling-merchants"] == "merchant-id"
            assert request.url.params["categories"] == "GROCERY"
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "event-id",
                        "code": "PLC",
                        "orderId": "order-id",
                        "merchantId": "merchant-id",
                    }
                ],
            )
        if path == "/events/v1.0/events/acknowledgment":
            assert json.loads(request.content) == [{"id": "event-id"}]
            return httpx.Response(202)
        if path == "/order/v1.0/orders/order-id":
            return httpx.Response(200, json={"id": "order-id", "status": "PLACED"})
        if path.endswith("/cancellationReasons"):
            return httpx.Response(
                200, json={"reasons": [{"code": "503", "description": "Item"}]}
            )
        if path.endswith("/validatePickupCode") or path.endswith("/verifyDeliveryCode"):
            return httpx.Response(200, json={"valid": True})
        return httpx.Response(202, json={"status": "ACCEPTED"})

    with IfoodClient(
        client_id="client",
        client_secret="secret",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.poll_events(["merchant-id"])[0]["id"] == "event-id"
        assert client.acknowledge_events(["event-id"])["status_code"] == 202
        assert client.get_order("order-id")["status"] == "PLACED"
        assert client.confirm_order("order-id")["status_code"] == 202
        assert client.start_order_preparation("order-id")["status_code"] == 202
        assert client.mark_order_ready("order-id")["status_code"] == 202
        assert client.dispatch_order("order-id")["status_code"] == 202
        assert client.cancellation_reasons("order-id")[0]["code"] == "503"
        assert (
            client.request_order_cancellation("order-id", "503")["status_code"] == 202
        )
        assert client.validate_pickup_code("order-id", "1234")["valid"] is True
        assert client.verify_delivery_code("order-id", "4321")["valid"] is True

    dispatch = next(
        request for request in requests if request.url.path.endswith("/dispatch")
    )
    assert json.loads(dispatch.content) == {"deliveredBy": "MERCHANT"}
    cancellation = next(
        request
        for request in requests
        if request.url.path.endswith("/requestCancellation")
    )
    assert json.loads(cancellation.content) == {"reason": "503"}
