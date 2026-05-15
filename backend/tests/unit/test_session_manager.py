from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

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


class _FakeQuery:
    def __init__(self, sessions):
        self.sessions = sessions
        self.criteria = []

    def filter(self, *criteria):
        self.criteria.extend(criteria)
        return self

    def all(self):
        filtered = self.sessions
        for criterion in self.criteria:
            field = getattr(getattr(criterion, "left", None), "name", None)
            value = getattr(getattr(criterion, "right", None), "value", None)
            if value is None and str(getattr(criterion, "right", "")).lower() == "false":
                value = False
            if value is None and str(getattr(criterion, "right", "")).lower() == "true":
                value = True
            operator_name = getattr(getattr(criterion, "operator", None), "__name__", "")
            if not field:
                continue
            if operator_name == "ne":
                filtered = [item for item in filtered if getattr(item, field) != value]
            else:
                filtered = [item for item in filtered if getattr(item, field) == value]
        return filtered


def test_revoke_all_sessions_can_be_limited_to_tenant():
    tenant_a = uuid4()
    tenant_b = uuid4()
    sessions = [
        SimpleNamespace(user_id=10, tenant_id=tenant_a, token_jti="a", revoked=False),
        SimpleNamespace(user_id=10, tenant_id=tenant_b, token_jti="b", revoked=False),
    ]
    query = _FakeQuery(sessions)
    db = Mock()
    db.query.return_value = query

    count = session_manager.revoke_all_sessions(
        db,
        user_id=10,
        reason="admin_forced_logout",
        tenant_id=tenant_a,
    )

    assert count == 1
    assert sessions[0].revoked is True
    assert sessions[0].revoke_reason == "admin_forced_logout"
    assert sessions[1].revoked is False
    assert any(
        getattr(getattr(criterion, "left", None), "name", None) == "tenant_id"
        for criterion in query.criteria
    )
    db.commit.assert_called_once()

