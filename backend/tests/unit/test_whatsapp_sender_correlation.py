from app.middlewares.request_context import clear_request_context, set_request_id
from app.utils.logger import clear_context
from app.whatsapp.sender import Dialog360Client, WahaClient


def teardown_function():
    clear_request_context()
    clear_context()


def test_dialog360_headers_include_active_correlation_without_leaking_api_key():
    set_request_id("req-wa-360")
    client = Dialog360Client("api-key-test")

    headers = client._headers_with_correlation("5511999999999")

    assert headers["D360-API-KEY"] == "api-key-test"
    assert headers["X-Correlation-ID"] == "req-wa-360"
    assert headers["X-Request-ID"] == "req-wa-360"


def test_waha_headers_include_active_correlation():
    set_request_id("req-waha")
    client = WahaClient("waha-key", "http://waha:3000")

    headers = client._headers_with_correlation("5511999999999")

    assert headers["X-Api-Key"] == "waha-key"
    assert headers["X-Correlation-ID"] == "req-waha"
    assert headers["X-Request-ID"] == "req-waha"

