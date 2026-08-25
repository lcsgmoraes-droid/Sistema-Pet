from types import SimpleNamespace

from app.campaigns import scheduler_seed


class _FakeSeedSession:
    def __init__(self, dialect_name):
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect_name))
        self.executed = []

    def get_bind(self):
        return self.bind

    def execute(self, statement, params):
        self.executed.append((str(statement), params))


def test_campaign_seed_uses_tenant_advisory_lock_only_on_postgresql():
    postgres = _FakeSeedSession("postgresql")
    sqlite = _FakeSeedSession("sqlite")

    scheduler_seed._bloquear_seed_concorrente(postgres, "tenant-demo")
    scheduler_seed._bloquear_seed_concorrente(sqlite, "tenant-demo")

    assert len(postgres.executed) == 1
    statement, params = postgres.executed[0]
    assert "pg_advisory_xact_lock" in statement
    assert params == {"lock_key": "corepet:campaign-seed:tenant-demo"}
    assert sqlite.executed == []
