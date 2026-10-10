from types import SimpleNamespace

from app.campaigns import scheduler_seed
from app.campaigns import models as campaign_models


class _FakeCampaign:
    campaign_type = object()
    tenant_id = object()

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeCampaignQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return []


class _FakeSeedSession:
    def __init__(self, dialect_name):
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect_name))
        self.executed = []
        self.added = []
        self.commit_count = 0

    def get_bind(self):
        return self.bind

    def execute(self, statement, params):
        self.executed.append((str(statement), params))

    def query(self, *_args, **_kwargs):
        return _FakeCampaignQuery()

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commit_count += 1


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


def test_campaign_seed_creates_every_default_campaign_paused(monkeypatch):
    db = _FakeSeedSession("sqlite")
    monkeypatch.setattr(campaign_models, "Campaign", _FakeCampaign)

    created = scheduler_seed.seed_campaigns_for_tenant(db, "tenant-demo")

    assert created == len(scheduler_seed._DEFAULT_CAMPAIGNS)
    assert len(db.added) == created
    assert all(
        campaign.status == campaign_models.CampaignStatusEnum.paused
        for campaign in db.added
    )
    assert db.commit_count == 1
