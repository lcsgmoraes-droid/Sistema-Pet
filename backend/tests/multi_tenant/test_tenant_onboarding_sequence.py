from app.services import tenant_onboarding_service as onboarding_service
from tests.multi_tenant.tenant_onboarding_test_helpers import TENANT_A


def test_onboarding_syncs_postgres_sequence_before_known_table_insert(monkeypatch):
    calls = []

    class _Result:
        def __init__(self, value=None):
            self._value = value

        def scalar(self):
            return self._value

    class _Dialect:
        name = "postgresql"

    class _Bind:
        dialect = _Dialect()

    class _FakeSession:
        def __init__(self):
            self.info = {}

        def get_bind(self):
            return _Bind()

        def execute(self, statement, params=None):
            sql = str(statement)
            calls.append(("db.execute", sql, params or {}))
            if "pg_get_serial_sequence" in sql:
                return _Result("public.contas_bancarias_id_seq")
            return _Result()

    def _fake_execute_tenant_safe(db, sql, params, tenant_id, require_tenant):
        calls.append(("execute_tenant_safe", sql, params, tenant_id, require_tenant))

    monkeypatch.setattr(
        onboarding_service, "execute_tenant_safe", _fake_execute_tenant_safe
    )

    onboarding_service._execute_insert(
        _FakeSession(),
        """
        INSERT INTO contas_bancarias (tenant_id, nome)
        VALUES (:tenant_id, :nome)
        """,
        {"tenant_id": TENANT_A, "nome": "Caixa"},
        TENANT_A,
    )

    assert calls[0][0] == "db.execute"
    assert "pg_get_serial_sequence" in calls[0][1]
    assert calls[1][0] == "db.execute"
    assert "setval" in calls[1][1]
    assert calls[2][0] == "execute_tenant_safe"
