from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import app.session_manager as session_manager


def test_validate_session_does_not_touch_last_activity(monkeypatch):
    previous_activity = datetime(2026, 5, 15, 1, 0, tzinfo=timezone.utc)
    db_session = SimpleNamespace(
        revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        last_activity_at=previous_activity,
    )
    db = Mock()

    monkeypatch.setattr(
        session_manager,
        "get_session_by_jti",
        lambda _db, _token_jti: db_session,
    )

    assert session_manager.validate_session(db, "session-jti") is True
    assert db_session.last_activity_at == previous_activity
    db.flush.assert_not_called()

