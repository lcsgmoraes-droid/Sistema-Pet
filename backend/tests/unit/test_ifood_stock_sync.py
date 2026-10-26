"""Fila DEV: latest-value, falhas e recuperacao com provedor sem rede."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.ifood_catalog_models import (
    IfoodCatalogConfirmation as Confirmation,
    IfoodCatalogLink as Link,
    IfoodCatalogSubmission as Submission,
    IfoodStockSyncState as State,
)
from app.ifood_integration_models import IfoodMerchantConfig
from app.integrations.ifood import stock_sync as sync
from app.integrations.ifood.client import IfoodClientError
from tests.unit.test_ifood_management import api  # noqa: F401

START = datetime(2030, 1, 2, 12, tzinfo=timezone.utc)
LATER = START + timedelta(seconds=sync.COOLDOWN_SECONDS)


@pytest.fixture
def pilot(api, monkeypatch):  # noqa: F811
    State.__table__.create(api.engine, checkfirst=True)
    for name in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    api.first.codigo = sync.PILOT_SKU
    api.first.codigo_barras = sync.PILOT_BARCODE
    api.first.estoque_atual = 21
    api.first.preco_ifood = 154.90
    merchant = str(uuid4())
    config = IfoodMerchantConfig(
        tenant_id=api.tenant, merchant_id=merchant, active=True, stock_safety=0
    )
    link = Link(
        tenant_id=api.tenant,
        merchant_id=merchant,
        product_id=api.first.id,
        barcode=sync.PILOT_BARCODE,
        mode="existing",
        revision=1,
        portal_checked_at=START - timedelta(days=1),
        portal_checked_by=1,
    )
    api.db.add_all([config, link])
    api.db.flush()
    confirmation = Confirmation(
        tenant_id=api.tenant,
        link_id=link.id,
        barcode=sync.PILOT_BARCODE,
        kind="link",
        present=True,
        portal_active=True,
        stock=21,
        price=154.90,
        actor_id=1,
        confirmed_at=START - timedelta(days=1),
    )
    api.db.add(confirmation)
    api.db.commit()
    for key, value in {
        "ENVIRONMENT": "development",
        "IFOOD_CATALOG_WRITE_ENABLED": True,
        "IFOOD_STOCK_SYNC_DEV_ENABLED": True,
        "IFOOD_STOCK_SYNC_LIVE_ENABLED": False,
        "IFOOD_STOCK_SYNC_POLLING_ENABLED": True,
        "IFOOD_STOCK_SYNC_TENANT_ID": str(api.tenant),
        "IFOOD_STOCK_SYNC_MERCHANT_ID": merchant,
        "IFOOD_STOCK_SYNC_PRODUCT_ID": api.first.id,
        "IFOOD_STOCK_SYNC_SKU": sync.PILOT_SKU,
        "IFOOD_STOCK_SYNC_BARCODE": sync.PILOT_BARCODE,
        "IFOOD_API_BASE_URL": "http://127.0.0.1:9",
        "IFOOD_CLIENT_ID": "fixture-client",
        "IFOOD_CLIENT_SECRET": "fixture-not-a-secret",
    }.items():
        monkeypatch.setattr(settings, key, value)

    class Client:
        def __init__(self):
            self.calls = []
            self.error = None

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def ingest_items(self, merchant_id, items, **kwargs):
            self.calls.append((merchant_id, deepcopy(items), kwargs))
            if self.error is not None:
                raise self.error
            return {
                "status_code": 202,
                "response": {"requestId": str(uuid4()), "private": "never-persist"},
            }

    client = Client()

    def tick(now=START, **overrides):
        api.db.commit()
        result = sync.poll_ifood_stock_once(
            client_factory=lambda: client,
            session_factory=lambda: Session(api.engine),
            now=now,
            **overrides,
        )
        api.db.expire_all()
        return result

    return SimpleNamespace(
        **vars(api),
        merchant=merchant,
        config=config,
        link=link,
        confirmation=confirmation,
        provider=client,
        tick=tick,
    )


@pytest.mark.parametrize(
    "name",
    [
        "IFOOD_STOCK_SYNC_DEV_ENABLED",
        "IFOOD_STOCK_SYNC_POLLING_ENABLED",
        "IFOOD_CATALOG_WRITE_ENABLED",
    ],
)
def test_disabled_flags_never_open_session(pilot, monkeypatch, name):
    monkeypatch.setattr(settings, name, False)
    result = sync.poll_ifood_stock_once(
        session_factory=lambda: pytest.fail("DB must stay closed")
    )
    assert result["status"] == "disabled"
    assert not pilot.provider.calls


@pytest.mark.parametrize("alias", ["APP_ENV", "ENV", "ENVIRONMENT"])
@pytest.mark.parametrize("environment", ["production", "prod", "staging", " PROD "])
def test_runtime_aliases_fail_closed_before_db(pilot, monkeypatch, alias, environment):
    monkeypatch.setenv(alias, environment)
    assert sync.poll_ifood_stock_once(
        session_factory=lambda: pytest.fail("DB must stay closed")
    ) == {"status": "disabled", "reason": "dev_only"}


@pytest.mark.parametrize(
    "url",
    [
        "https://merchant-api.ifood.com.br",
        "http://example.com",
        "https://localhost:9",
        "http://127.0.0.1@evil.invalid",
        "http://user:password@localhost:9",
        "http://127.0.0.1:9/other",
        "http://localhost:9?target=external",
        "http://localhost:9#fragment",
        "http://localhost:70000",
        "http://127.1:9",
    ],
)
def test_provider_must_be_exact_local_url_even_with_injected_factory(
    pilot, monkeypatch, url
):
    monkeypatch.setattr(settings, "IFOOD_API_BASE_URL", url)
    assert (
        sync.poll_ifood_stock_once(
            client_factory=lambda: pytest.fail("No provider"),
            session_factory=lambda: pytest.fail("No DB"),
        )["reason"]
        == "provider_not_local"
    )


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1:9", "http://localhost:8766/", "http://[::1]:8766"]
)
def test_local_url_whitelist(url):
    assert sync._local_provider(url)


@pytest.mark.parametrize(
    "field,value",
    [
        ("IFOOD_STOCK_SYNC_TENANT_ID", "not-uuid"),
        ("IFOOD_STOCK_SYNC_MERCHANT_ID", ""),
        ("IFOOD_STOCK_SYNC_PRODUCT_ID", 0),
        ("IFOOD_STOCK_SYNC_SKU", "018631.1"),
        ("IFOOD_STOCK_SYNC_BARCODE", "4006381333931"),
        ("IFOOD_CLIENT_SECRET", ""),
    ],
)
def test_exact_scope_required_before_db(pilot, monkeypatch, field, value):
    monkeypatch.setattr(settings, field, value)
    assert (
        sync.poll_ifood_stock_once(session_factory=lambda: pytest.fail("No DB"))[
            "status"
        ]
        == "disabled"
    )


def test_baseline_latest_value_cooldown_and_stock_only_payload(pilot):
    p = pilot
    assert p.tick()["status"] == "unchanged"
    row = p.db.query(State).one()
    assert row.last_accepted_stock == 21 and row.reference_source == "portal"
    p.first.estoque_atual = 20
    assert p.tick()["status"] == "accepted"
    assert p.tick()["status"] == "unchanged"
    p.first.estoque_atual = 19
    assert p.tick(START + timedelta(minutes=1))["status"] == "cooldown"
    p.first.estoque_atual = 18
    assert p.tick(LATER)["sent_stock"] == 18
    assert len(p.provider.calls) == 2
    for _, items, args in p.provider.calls:
        assert set(items[0]) == {"barcode", "inventory"}
        assert items[0]["barcode"] == sync.PILOT_BARCODE
        assert set(items[0]["inventory"]) == {"stock"}
        assert args == {"method": "PATCH", "reset_catalog": False}
    assert p.first.preco_ifood == 154.90 and p.first.preco_venda == 100
    assert p.other.estoque_atual == 5 and p.other.preco_venda == 100
    rows = p.db.query(Submission).all()
    assert all(row.source == "auto_stock" and row.fields == ["stock"] for row in rows)
    assert "never-persist" not in str([row.evidence for row in rows])
    view = sync.stock_sync_view(p.db, p.tenant, p.merchant, p.first.id)
    assert (
        view["reference_source"] == "api_acceptance"
        and view["external_confirmed"] is False
    )


@pytest.mark.parametrize(
    "case", ["missing", "absent", "inactive", "unknown_active", "stock_unknown"]
)
def test_requires_human_baseline_before_first_send(pilot, case):
    p = pilot
    if case == "missing":
        p.db.delete(p.confirmation)
    elif case == "absent":
        p.confirmation.present = False
    elif case == "inactive":
        p.confirmation.portal_active = False
    elif case == "unknown_active":
        p.confirmation.portal_active = None
    else:
        p.confirmation.stock = None
    p.first.estoque_atual = 20
    assert p.tick()["reason"] == "initial_confirmation_required"
    assert not p.provider.calls and p.db.query(Submission).count() == 0


@pytest.mark.parametrize("value", [None, float("inf"), -1, 20.5, 1_000_001])
def test_invalid_or_unknown_physical_stock_is_not_zero(pilot, value):
    p = pilot
    p.first.estoque_atual = value
    assert p.tick()["reason"] == "stock_invalid"
    assert not p.provider.calls


def test_reservations_safety_pause_and_resume(pilot, monkeypatch):
    from app.estoque_reserva_service import EstoqueReservaService

    p = pilot
    monkeypatch.setattr(
        EstoqueReservaService,
        "mapa_reservas_ativas_por_produto",
        lambda *_: {p.first.id: 3},
    )
    p.config.stock_safety = 2
    assert p.tick()["sent_stock"] == 16
    p.first.ifood_pausado = True
    assert p.tick(LATER)["sent_stock"] == 0
    p.first.ifood_pausado = False
    assert p.tick(LATER + timedelta(seconds=sync.COOLDOWN_SECONDS))["sent_stock"] == 16
    assert p.first.estoque_atual == 21


@pytest.mark.parametrize(
    "http_status,status",
    [(400, "blocked"), (401, "blocked"), (500, "uncertain"), (None, "uncertain")],
)
def test_failures_are_durable_and_never_blindly_repeated(pilot, http_status, status):
    p = pilot
    p.first.estoque_atual = 20
    p.provider.error = IfoodClientError(
        "private-must-not-persist", status_code=http_status
    )
    assert p.tick()["status"] == status
    assert p.tick(LATER + timedelta(days=1))["status"] == status
    assert len(p.provider.calls) == 1
    row = p.db.query(Submission).one()
    assert "private" not in str(row.evidence) and "private" not in row.error_code


def test_rate_limit_backoff_latest_value_and_bounded_retries(pilot):
    p = pilot
    p.first.estoque_atual = 20
    p.provider.error = IfoodClientError("rate limit", status_code=429)
    assert p.tick()["status"] == "backoff"
    p.first.estoque_atual = 19
    assert p.tick(START + timedelta(seconds=30))["status"] == "backoff"
    assert len(p.provider.calls) == 1
    for attempt in range(1, sync.MAX_RATE_LIMIT_RETRIES):
        assert (
            p.tick(START + timedelta(seconds=attempt * sync.COOLDOWN_SECONDS))["status"]
            == "backoff"
        )
    assert p.tick(START + timedelta(days=1))["reason"] == "retry_limit"
    assert len(p.provider.calls) == sync.MAX_RATE_LIMIT_RETRIES
    assert p.provider.calls[-1][1][0]["inventory"]["stock"] == 19


def test_manual_pending_accepted_is_not_overridden(pilot):
    p = pilot
    p.db.add(
        Submission(
            tenant_id=p.tenant,
            link_id=p.link.id,
            merchant_id=p.merchant,
            barcode=sync.PILOT_BARCODE,
            request_key=str(uuid4()),
            operation="update",
            fields=["stock"],
            payload_hash="a" * 64,
            evidence={"barcode": sync.PILOT_BARCODE, "inventory": {"stock": 21}},
            status="accepted",
            actor_id=1,
            created_at=START,
        )
    )
    p.first.estoque_atual = 20
    assert p.tick(LATER)["reason"] == "manual_pending"
    assert not p.provider.calls


@pytest.mark.parametrize("orphan_sending", [False, True])
def test_explicit_portal_review_recovers_uncertain_and_crash_with_revision(
    pilot, orphan_sending
):
    p = pilot
    p.first.estoque_atual = 20
    p.provider.error = IfoodClientError("uncertain", status_code=500)
    assert p.tick()["status"] == "uncertain"
    if orphan_sending:
        p.db.query(Submission).one().status = "sending"
        p.db.commit()
    assert p.tick(LATER)["status"] == "uncertain"
    p.link.revision += 1
    p.db.add(
        Confirmation(
            tenant_id=p.tenant,
            link_id=p.link.id,
            barcode=sync.PILOT_BARCODE,
            kind="portal",
            present=True,
            portal_active=True,
            stock=21,
            price=154.90,
            actor_id=1,
            confirmed_at=LATER + timedelta(seconds=1),
        )
    )
    p.provider.error = None
    assert p.tick(LATER + timedelta(seconds=2))["status"] == "accepted"
    assert p.tick(LATER + timedelta(seconds=3))["status"] == "unchanged"
    assert len(p.provider.calls) == 2


def test_unreviewed_link_revision_and_identity_drift_block_and_persist(pilot):
    p = pilot
    assert p.tick()["status"] == "unchanged"
    p.link.revision += 1
    assert p.tick()["reason"] == "link_revision_changed"
    p.first.codigo_barras = "4006381333931"
    assert p.tick()["reason"] == "product_identity_changed"
    assert p.db.query(State).one().error_code == "product_identity_changed"
    assert not p.provider.calls


def test_config_flag_changed_after_durable_claim_aborts_before_http(pilot, monkeypatch):
    p = pilot
    p.first.estoque_atual = 20
    p.db.commit()

    class ChangingSession(Session):
        commits = 0

        def commit(self):
            super().commit()
            self.commits += 1
            if self.commits == 2:
                monkeypatch.setattr(settings, "IFOOD_STOCK_SYNC_DEV_ENABLED", False)

    result = sync.poll_ifood_stock_once(
        client_factory=lambda: p.provider,
        session_factory=lambda: ChangingSession(p.engine),
        now=START,
    )
    assert result == {
        "status": "blocked",
        "reason": "scope_changed",
        "request_key": result["request_key"],
    }
    assert not p.provider.calls
    p.db.expire_all()
    row = p.db.query(Submission).one()
    assert row.status == "error" and row.error_code == "dispatch_aborted"
    monkeypatch.setattr(settings, "IFOOD_STOCK_SYNC_DEV_ENABLED", True)
    assert p.tick(START + timedelta(seconds=1))["status"] == "accepted"


def test_scheduler_uses_existing_scheduler_only_and_respects_guard(pilot, monkeypatch):
    calls = []
    scheduler = SimpleNamespace(
        add_job=lambda *args, **kwargs: calls.append((args, kwargs))
    )
    assert sync.register_stock_sync_job(scheduler)
    assert calls[0][1]["max_instances"] == 1 and calls[0][1]["coalesce"] is True
    monkeypatch.setattr(
        settings, "IFOOD_API_BASE_URL", "https://merchant-api.ifood.com.br"
    )
    assert not sync.register_stock_sync_job(scheduler)
    assert len(calls) == 1


def test_default_client_captures_local_url_and_disables_env_proxies(pilot, monkeypatch):
    captured = []
    monkeypatch.setattr(sync, "IfoodClient", lambda **kwargs: captured.append(kwargs))
    sync._client()
    assert (
        captured[0]["base_url"] == "http://127.0.0.1:9"
        and captured[0]["trust_env"] is False
    )
    monkeypatch.setattr(
        settings, "IFOOD_API_BASE_URL", "https://merchant-api.ifood.com.br"
    )
    with pytest.raises(IfoodClientError):
        sync._client()
    assert len(captured) == 1
