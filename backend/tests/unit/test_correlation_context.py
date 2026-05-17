from app.middlewares.request_context import clear_request_context, get_request_id, set_request_id
from app.utils.logger import clear_context, get_trace_id, set_trace_id


def teardown_function():
    clear_request_context()
    clear_context()


def test_derive_correlation_id_is_stable_safe_and_short():
    from app.utils.correlation import derive_correlation_id

    first = derive_correlation_id("job.bling webhook", "event:abc/123")
    second = derive_correlation_id("job.bling webhook", "event:abc/123")

    assert first == second
    assert first.startswith("job.bling-webhook-")
    assert len(first) <= 80
    assert ":" not in first
    assert "/" not in first


def test_operation_correlation_context_sets_and_restores_request_and_trace():
    from app.utils.correlation import operation_correlation_context

    set_request_id("req-http-1")
    set_trace_id("trace-http-1")

    with operation_correlation_context("job.test", correlation_id="job-test-123") as correlation_id:
        assert correlation_id == "job-test-123"
        assert get_request_id() == "job-test-123"
        assert get_trace_id() == "job-test-123"

    assert get_request_id() == "req-http-1"
    assert get_trace_id() == "trace-http-1"


def test_current_correlation_id_reuses_active_request_id():
    from app.utils.correlation import current_correlation_id

    set_request_id("req-active")

    assert current_correlation_id("job.any") == "req-active"

