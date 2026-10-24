from datetime import date
from uuid import uuid4

import httpx
import pytest

from app.integrations.ifood.client import IfoodClientError
from app.integrations.ifood.financial_client import IfoodFinancialClient


MERCHANT = str(uuid4())
BEGIN, END = date(2026, 10, 5), date(2026, 10, 11)


def client(handler):
    return IfoodFinancialClient(
        client_id="test-client",
        client_secret="private-test-secret",
        transport=httpx.MockTransport(handler),
    )


def test_reads_all_pages_in_homologation_without_any_operational_writes():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/authentication/v1.0/oauth/token":
            return httpx.Response(
                200, json={"accessToken": "private-test-token", "expiresIn": 3600}
            )
        assert request.method == "GET"
        assert (
            request.url.path == f"/financial/v3.0/merchants/{MERCHANT}/financial-events"
        )
        assert request.headers["x-request-homologation"] == "true"
        assert request.url.params["beginDate"] == BEGIN.isoformat()
        assert request.url.params["endDate"] == END.isoformat()
        assert request.url.params["size"] == "100"
        page = int(request.url.params["page"])
        return httpx.Response(
            200,
            json={
                "page": page,
                "size": 100,
                "hasNextPage": page == 1,
                "financialEvents": [{"amount": {"value": "-3.42"}}],
            },
        )

    with client(handler) as api:
        pages = api.fetch_financial_pages(MERCHANT, BEGIN, END)
    assert len(pages) == 2
    assert pages[0]["financialEvents"][0]["amount"]["value"] == "-3.42"
    assert len(requests) == 3


@pytest.mark.parametrize("code", [403, 429, 500])
def test_sanitizes_provider_failure_and_does_not_retry_or_return_partial_data(code):
    calls = []

    def handler(request):
        if "oauth/token" in request.url.path:
            return httpx.Response(200, json={"accessToken": "token", "expiresIn": 3600})
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(
                200, json={"page": 1, "hasNextPage": True, "financialEvents": [{}]}
            )
        return httpx.Response(
            code, json={"message": "private-test-secret private-test-token"}
        )

    with client(handler) as api, pytest.raises(IfoodClientError) as caught:
        api.fetch_financial_pages(MERCHANT, BEGIN, END)
    assert caught.value.status_code == code
    assert "private-test" not in str(caught.value)
    assert len(calls) == 2


def test_renews_token_once_for_401_on_idempotent_financial_read():
    auth_count = 0
    get_count = 0

    def handler(request):
        nonlocal auth_count, get_count
        if "oauth/token" in request.url.path:
            auth_count += 1
            return httpx.Response(
                200, json={"accessToken": f"token-{auth_count}", "expiresIn": 3600}
            )
        get_count += 1
        if get_count == 1:
            return httpx.Response(401)
        assert request.headers["Authorization"] == "Bearer token-2"
        return httpx.Response(
            200, json={"page": 1, "hasNextPage": False, "financialEvents": []}
        )

    with client(handler) as api:
        assert len(api.fetch_financial_pages(MERCHANT, BEGIN, END)) == 1
    assert auth_count == get_count == 2


def test_accepts_single_envelope_array_from_reference_example():
    def handler(request):
        if "oauth/token" in request.url.path:
            return httpx.Response(200, json={"accessToken": "token", "expiresIn": 3600})
        return httpx.Response(
            200, json=[{"page": 1, "hasNextPage": False, "financialEvents": []}]
        )

    with client(handler) as api:
        assert api.fetch_financial_pages(MERCHANT, BEGIN, END) == [
            {"page": 1, "hasNextPage": False, "financialEvents": []}
        ]


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"page": 2, "hasNextPage": False, "financialEvents": []},
        {"page": True, "hasNextPage": False, "financialEvents": []},
        {"page": 1, "hasNextPage": "false", "financialEvents": []},
        {"page": 1, "hasNextPage": True, "financialEvents": []},
    ],
)
def test_refuses_malformed_or_repeated_pages(payload):
    def handler(request):
        if "oauth/token" in request.url.path:
            return httpx.Response(200, json={"accessToken": "token", "expiresIn": 3600})
        return httpx.Response(200, json=payload)

    with client(handler) as api, pytest.raises(IfoodClientError):
        api.fetch_financial_pages(MERCHANT, BEGIN, END)


@pytest.mark.parametrize(
    "merchant,begin,end",
    [
        ("../item", BEGIN, END),
        (MERCHANT, END, BEGIN),
        (MERCHANT, date(2026, 1, 1), date(2026, 2, 3)),
    ],
)
def test_refuses_invalid_target_or_window_before_network(merchant, begin, end):
    def handler(request):
        pytest.fail("Invalid request must not make network calls")

    with client(handler) as api, pytest.raises(IfoodClientError):
        api.fetch_financial_pages(merchant, begin, end)
