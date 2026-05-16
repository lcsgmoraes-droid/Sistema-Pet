import json
from types import SimpleNamespace
from uuid import UUID

from app.middlewares.request_context import clear_request_context, set_request_id
from app.services import auth_security


def test_register_successful_login_includes_request_id(monkeypatch):
    captured = {}

    def fake_log_action(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(auth_security, "log_action", fake_log_action)
    set_request_id("req-auth-123")
    user = SimpleNamespace(
        id=7,
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        failed_login_attempts=3,
        locked_until=None,
    )
    request = SimpleNamespace(
        headers={"user-agent": "pytest-agent"},
        client=SimpleNamespace(host="127.0.0.1"),
    )

    try:
        auth_security.register_successful_login(db=object(), user=user, request=request)
    finally:
        clear_request_context()

    details = json.loads(captured["details"])
    assert captured["action"] == "auth.login_success"
    assert captured["tenant_id"] == UUID("11111111-1111-1111-1111-111111111111")
    assert details["request_id"] == "req-auth-123"
    assert details["success"] is True
