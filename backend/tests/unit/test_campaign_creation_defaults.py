from types import SimpleNamespace
from uuid import uuid4

from app.campaigns import engajamento_routes, ranking_routes
from app.campaigns.models import Campaign, CampaignStatusEnum


class _FakeCampaign:
    def __init__(self, **kwargs):
        self.id = None
        self.created_at = None
        self.__dict__.update(kwargs)


class _CreateSession:
    def __init__(self):
        self.added = []
        self.commit_count = 0

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commit_count += 1

    def refresh(self, item):
        item.id = 1


def _user_and_tenant():
    return SimpleNamespace(id=1), uuid4()


def test_campaign_model_uses_paused_as_safe_default():
    assert Campaign.__table__.c.status.default.arg == CampaignStatusEnum.paused


def test_new_retention_campaign_starts_paused(monkeypatch):
    db = _CreateSession()
    monkeypatch.setattr(engajamento_routes, "Campaign", _FakeCampaign)

    result = engajamento_routes.criar_retencao(
        engajamento_routes.RetencaoBody(name="Clientes inativos"),
        db=db,
        user_and_tenant=_user_and_tenant(),
    )

    assert db.added[0].status == CampaignStatusEnum.paused
    assert result["status"] == CampaignStatusEnum.paused.value
    assert db.commit_count == 1


def test_new_custom_campaign_starts_paused(monkeypatch):
    db = _CreateSession()
    monkeypatch.setattr(ranking_routes, "Campaign", _FakeCampaign)

    result = ranking_routes.criar_campanha(
        ranking_routes.CriarCampanhaBody(
            name="Recompra configurada",
            campaign_type="quick_repurchase",
        ),
        db=db,
        user_and_tenant=_user_and_tenant(),
    )

    assert db.added[0].status == CampaignStatusEnum.paused
    assert result["status"] == CampaignStatusEnum.paused
    assert db.commit_count == 1
