from ops_api_mcp.security import redact_text, redact_value, validate_local_http_url


def test_redact_text_masks_common_secret_shapes():
    text = "Authorization: Bearer abc.def token=secret password=123"

    redacted = redact_text(text)

    assert "abc.def" not in redacted
    assert "secret" not in redacted
    assert "123" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_value_masks_secret_keys_recursively():
    payload = {
        "access_token": "token-real",
        "nested": {"password": "senha-real", "name": "Lucas"},
    }

    assert redact_value(payload) == {
        "access_token": "[REDACTED]",
        "nested": {"password": "[REDACTED]", "name": "Lucas"},
    }


def test_validate_local_http_url_blocks_external_host():
    try:
        validate_local_http_url("https://example.com/health", ("localhost",))
    except ValueError as exc:
        assert "Host nao permitido" in str(exc)
    else:
        raise AssertionError("external host should be blocked")
