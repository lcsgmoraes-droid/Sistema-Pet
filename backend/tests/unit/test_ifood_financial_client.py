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


REQUEST_ID = str(uuid4())
MONTH = "2025-08"
SIGNED_URL = "https://payout-platform-api-files-sandbox.s3.amazonaws.com/reconciliacao-externa/on-demand/test.csv.gz?X-Amz-Signature=private-example"


def authenticated(handler):
    def transport(request):
        if "oauth/token" in request.url.path:
            return httpx.Response(
                200, json={"accessToken": "private-test-token", "expiresIn": 3600}
            )
        return handler(request)

    return client(transport)


def settlement_body():
    return dict(
        merchantId=MERCHANT,
        beginDate=str(BEGIN),
        endDate=str(END),
        balance=0,
        settlements=[
            dict(
                startDateCalculation=str(BEGIN),
                endDateCalculation=str(END),
                closingItems=[
                    dict(
                        id="111",
                        type="REPASSE",
                        amount=12.34,
                        status="SUCCEED",
                        paymentDate="2026-11-04",
                    ),
                    dict(id="112", type="BOLETO", amount=-12.34, status="PENDING"),
                ],
            ),
            dict(id="113", type="REGISTRO_RECEBIVEIS", amount=0, status="SUCCEED"),
        ],
    )


@pytest.mark.parametrize(
    "basis,prefix", [("calculation", "Calculation"), ("payment", "Payment")]
)
def test_settlements_uses_real_query_names_and_preserves_titles_without_summing(
    basis, prefix
):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == f"/financial/v3.0/merchants/{MERCHANT}/settlements"
        assert dict(request.url.params) == {
            f"begin{prefix}Date": str(BEGIN),
            f"end{prefix}Date": str(END),
        }
        assert request.headers["x-request-homologation"] == "true"
        return httpx.Response(200, json=[settlement_body()])

    with authenticated(handler) as api:
        body = api.fetch_settlements(MERCHANT, BEGIN, END, basis)
    assert body["balance"] == "0.00"
    assert body["settlements"][0]["closingItems"][1]["amount"] == "-12.34"
    assert body["settlements"][1]["amount"] == "0.00"


@pytest.mark.parametrize(
    "changes",
    [
        dict(merchantId=str(uuid4())),
        dict(beginDate="2026-10-01"),
        dict(balance=None),
        dict(consolidatedMerchants=[str(uuid4())]),
        dict(settlements=[{}]),
        dict(
            settlements=[dict(id="x", type="REPASSE", status="SUCCEED", amount="NaN")]
        ),
    ],
)
def test_settlements_rejects_other_store_incomplete_scope_and_invalid_amounts(changes):
    with authenticated(
        lambda _: httpx.Response(200, json=settlement_body() | changes)
    ) as api:
        with pytest.raises(IfoodClientError):
            api.fetch_settlements(MERCHANT, BEGIN, END)


@pytest.mark.parametrize("code", [200, 202])
def test_create_reconciliation_uses_documented_post_body_and_accepts_202(code):
    def handler(request):
        import json

        assert request.method == "POST"
        assert (
            request.url.path
            == f"/financial/v3.0/merchants/{MERCHANT}/reconciliation/on-demand"
        )
        assert json.loads(request.content) == {"competence": MONTH}
        assert request.headers["x-request-homologation"] == "true"
        return httpx.Response(
            code, json=dict(merchantId=MERCHANT, competence=MONTH, requestId=REQUEST_ID)
        )

    with authenticated(handler) as api:
        result = api.create_reconciliation(MERCHANT, MONTH)
    assert result == dict(
        merchant_id=MERCHANT,
        competence=MONTH,
        request_id=REQUEST_ID,
        status="created",
        download_url=None,
    )


def test_conflict_never_invents_a_request_id_or_repeats_post():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(409, json={"message": "private-test-secret"})

    with authenticated(handler) as api:
        result = api.create_reconciliation(MERCHANT, MONTH)
    assert result["status"] == "conflict" and result["request_id"] is None
    assert len(requests) == 1 and "private-test" not in repr(result)


@pytest.mark.parametrize("status", ["created", "enqueue", "error"])
def test_reconciliation_pending_and_provider_error_do_not_become_ready_or_zero(status):
    def handler(request):
        assert request.url.path.endswith(f"/reconciliation/on-demand/{REQUEST_ID}")
        return httpx.Response(
            200,
            json=dict(
                id=REQUEST_ID,
                merchantId=MERCHANT,
                competence=MONTH,
                status=status,
                errorMessage="private details",
            ),
        )

    with authenticated(handler) as api:
        result = api.get_reconciliation(MERCHANT, REQUEST_ID, MONTH)
    assert result["status"] == status and result["download_url"] is None
    assert "private details" not in repr(result)
    assert result["error_code"] == ("provider_job_error" if status == "error" else None)


@pytest.mark.parametrize(
    "field,detail",
    [
        (
            "errorMessage",
            f"File generation failed: No financial entries exist for merchant {MERCHANT} in the requested time frame.",
        ),
        (
            "message",
            "No financial entries found for the specified merchant and competence.",
        ),
    ],
)
def test_documented_no_entries_examples_return_only_local_allowlisted_reason(
    field, detail
):
    body = dict(id=REQUEST_ID, merchantId=MERCHANT, competence=MONTH, status="error")
    body[field] = detail
    with authenticated(lambda _: httpx.Response(200, json=body)) as api:
        result = api.get_reconciliation(MERCHANT, REQUEST_ID, MONTH)
    assert result["status"] == "error" and result["download_url"] is None
    assert result["error_code"] == "no_financial_entries"
    assert "errorMessage" not in result and "message" not in result
    assert detail not in repr(result)


@pytest.mark.parametrize(
    "detail",
    [
        "No financial entries exist. customer@example.test https://private.example.test/file?secret=PRIVATE",
        f"File generation failed: No financial entries exist for merchant {uuid4()} in the requested time frame.",
        f"File generation failed: No financial entries exist for merchant {MERCHANT} in the requested time frame. email@example.test",
        {"secret": "PRIVATE"},
        "PRIVATE" * 1000,
        None,
        "Limit exceeded for PRIVATE merchant",  # No undocumented substring heuristic.
    ],
)
def test_unknown_or_sensitive_job_details_remain_generic_and_are_never_copied(detail):
    body = dict(
        id=REQUEST_ID,
        merchantId=MERCHANT,
        competence=MONTH,
        status="error",
        errorMessage=detail,
    )
    with authenticated(lambda _: httpx.Response(200, json=body)) as api:
        result = api.get_reconciliation(MERCHANT, REQUEST_ID, MONTH)
    assert result["error_code"] == "provider_job_error"
    assert "PRIVATE" not in repr(result) and "@" not in repr(result)
    assert "private.example" not in repr(result)
    assert result["download_url"] is None and "errorMessage" not in result


def test_conflicting_error_message_fields_do_not_claim_known_no_entries_reason():
    body = dict(
        id=REQUEST_ID,
        merchantId=MERCHANT,
        competence=MONTH,
        status="error",
        errorMessage="No financial entries found for the specified merchant and competence.",
        message="Unrecognized failure PRIVATE",
    )
    with authenticated(lambda _: httpx.Response(200, json=body)) as api:
        result = api.get_reconciliation(MERCHANT, REQUEST_ID, MONTH)
    assert result["error_code"] == "provider_job_error"


@pytest.mark.parametrize("field", ["downloadPath", "filePath"])
def test_processed_file_accepts_both_verified_reference_url_fields(field):
    body = dict(
        id=REQUEST_ID, merchantId=MERCHANT, competence=MONTH, status="processed"
    )
    body[field] = SIGNED_URL
    with authenticated(lambda _: httpx.Response(200, json=body)) as api:
        assert (
            api.get_reconciliation(MERCHANT, REQUEST_ID, MONTH)["download_url"]
            == SIGNED_URL
        )


@pytest.mark.parametrize(
    "changes",
    [
        dict(merchantId=str(uuid4())),
        dict(id=str(uuid4())),
        dict(competence="2025-07"),
        dict(status="unknown"),
        dict(status="processed"),
        dict(
            status="processed",
            filePath=SIGNED_URL,
            downloadPath=SIGNED_URL + "different",
        ),
    ],
)
def test_job_scope_and_completion_must_be_unequivocal(changes):
    body = (
        dict(id=REQUEST_ID, merchantId=MERCHANT, competence=MONTH, status="created")
        | changes
    )
    with (
        authenticated(lambda _: httpx.Response(200, json=body)) as api,
        pytest.raises(IfoodClientError),
    ):
        api.get_reconciliation(MERCHANT, REQUEST_ID, MONTH)


def test_downloader_is_separate_from_api_session_and_does_not_send_auth_or_cookies():
    content = b"competencia;loja_id;valor;impacto_no_repasse\n"

    def handler(request):
        assert (
            request.method == "GET"
            and request.url.host == "payout-platform-api-files-sandbox.s3.amazonaws.com"
        )
        assert (
            "authorization" not in request.headers and "cookie" not in request.headers
        )
        assert "x-request-homologation" not in request.headers
        return httpx.Response(200, stream=httpx.ByteStream(content))

    with client(handler) as api:
        api._client.headers["Authorization"] = "private-api-secret"
        api._client.cookies.set("private-cookie", "private-value")
        assert api.download_statement(SIGNED_URL) == content


@pytest.mark.parametrize(
    "url",
    [
        "http://payout-platform-api-files-sandbox.s3.amazonaws.com/reconciliacao-externa/on-demand/test.csv",
        "https://127.0.0.1/reconciliacao-externa/on-demand/test.csv",
        "https://payout-platform-api-files-sandbox.s3.amazonaws.com.evil.example/reconciliacao-externa/on-demand/test.csv",
        "https://payout-platform-api-files-sandbox.s3.amazonaws.com:8443/reconciliacao-externa/on-demand/test.csv",
        "https://user:password@payout-platform-api-files-sandbox.s3.amazonaws.com/reconciliacao-externa/on-demand/test.csv",
        "https://payout-platform-api-files-sandbox.s3.amazonaws.com/other/test.csv",
        "https://payout-platform-api-files-sandbox.s3.amazonaws.com/reconciliacao-externa/on-demand/../test.csv",
        SIGNED_URL + "#fragment",
    ],
)
def test_download_rejects_unverified_hosts_url_confusion_and_path_traversal_before_network(
    url,
):
    with (
        client(lambda _: pytest.fail("Blocked URL made a network call")) as api,
        pytest.raises(IfoodClientError) as caught,
    ):
        api.download_statement(url)
    assert url not in str(caught.value)


@pytest.mark.parametrize("code", [301, 302, 307, 403])
def test_download_never_follows_redirects_or_reveals_signed_url(code):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(code, headers={"Location": "http://127.0.0.1/private"})

    with client(handler) as api, pytest.raises(IfoodClientError) as caught:
        api.download_statement(SIGNED_URL)
    assert len(calls) == 1 and "private-example" not in str(caught.value)


def test_download_limits_stream_bytes_and_sanitizes_network_error(monkeypatch):
    from app.integrations.ifood import financial_client as module

    monkeypatch.setattr(module, "MAX_DOWNLOAD_BYTES", 3)
    with (
        client(lambda _: httpx.Response(200, stream=httpx.ByteStream(b"1234"))) as api,
        pytest.raises(IfoodClientError),
    ):
        api.download_statement(SIGNED_URL)

    def handler(request):
        raise httpx.ConnectError("private-example signed url", request=request)

    with client(handler) as api, pytest.raises(IfoodClientError) as caught:
        api.download_statement(SIGNED_URL)
    assert (
        "private-example" not in str(caught.value) and caught.value.__suppress_context__
    )


def test_signed_url_is_not_written_to_httpx_info_logs_and_filter_is_removed(caplog):
    import logging

    logger = logging.getLogger("httpx")
    original = list(logger.filters)
    with caplog.at_level(logging.INFO, logger="httpx"):
        with client(
            lambda _: httpx.Response(200, stream=httpx.ByteStream(b"csv"))
        ) as api:
            assert api.download_statement(SIGNED_URL) == b"csv"
    assert "private-example" not in caplog.text
    assert logger.filters == original


def test_buffered_transport_download_is_bounded_too():
    with client(lambda _: httpx.Response(200, content=b"csv")) as api:
        assert api.download_statement(SIGNED_URL) == b"csv"


def test_settlement_ninety_day_inclusive_limit_is_checked_before_network():
    with client(lambda _: pytest.fail("Invalid period made a network call")) as api:
        with pytest.raises(IfoodClientError):
            api.fetch_settlements(MERCHANT, date(2025, 1, 1), date(2025, 4, 1))
