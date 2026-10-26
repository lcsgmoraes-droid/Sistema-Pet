"""Piloto LIVE com identidades efemeras e provedor injetado sem rede.

O teste configura o ambiente de producao, mas jamais instancia transporte real.
O hash de tenant e substituido somente na fixture para nao usar dados da loja.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import httpx
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
from app.integrations.ifood.catalog_pilot import submission_view
from app.integrations.ifood.client import IfoodClient, IfoodClientError
from tests.unit.test_ifood_management import api  # noqa: F401


START = datetime(2030, 1, 2, 12, tzinfo=timezone.utc)
LATER = START + timedelta(minutes=35)
MERCHANT = "adf87cbc-3858-413b-ae1e-3be36b1533e2"
BARCODE = "7898242031448"
PRODUCT = 5867


@pytest.fixture
def live(api, monkeypatch):  # noqa: F811
    real_client_factory = sync._client
    State.__table__.create(api.engine, checkfirst=True)
    for name in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.setenv(name, "production")
    monkeypatch.setattr(
        sync, "LIVE_TENANT_SHA256", sha256(str(api.tenant).encode()).hexdigest()
    )
    from app.produtos_models import Produto

    api.db.execute(
        Produto.__table__.insert().values(
            id=PRODUCT,
            tenant_id=api.tenant,
            user_id=1,
            codigo="227",
            nome="Produto piloto LIVE efemero",
            codigo_barras=BARCODE,
            gtin_ean=BARCODE,
            estoque_atual=21,
            preco_venda=100,
            preco_custo=60,
            preco_app=110,
            preco_ecommerce=120,
            preco_ifood=154.90,
            tipo_produto="SIMPLES",
            ativo=True,
            situacao=True,
            anunciar_ifood=True,
        )
    )
    api.first = api.db.get(Produto, PRODUCT)
    config = IfoodMerchantConfig(
        tenant_id=api.tenant, merchant_id=MERCHANT, active=True, stock_safety=0
    )
    link = Link(
        tenant_id=api.tenant,
        merchant_id=MERCHANT,
        product_id=PRODUCT,
        barcode=BARCODE,
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
        barcode=BARCODE,
        kind="portal",
        present=True,
        portal_active=True,
        stock=21,
        price=154.90,
        actor_id=1,
        confirmed_at=START - timedelta(days=1),
    )
    api.db.add(confirmation)
    api.db.commit()
    for name, value in {
        "ENVIRONMENT": "production",
        "IFOOD_CATALOG_WRITE_ENABLED": True,
        "IFOOD_STOCK_SYNC_DEV_ENABLED": False,
        "IFOOD_STOCK_SYNC_LIVE_ENABLED": True,
        "IFOOD_STOCK_SYNC_POLLING_ENABLED": True,
        "IFOOD_STOCK_SYNC_TENANT_ID": str(api.tenant),
        "IFOOD_STOCK_SYNC_MERCHANT_ID": MERCHANT,
        "IFOOD_STOCK_SYNC_PRODUCT_ID": PRODUCT,
        "IFOOD_STOCK_SYNC_SKU": "227",
        "IFOOD_STOCK_SYNC_BARCODE": BARCODE,
        "IFOOD_API_BASE_URL": "https://merchant-api.ifood.com.br",
        "IFOOD_CLIENT_ID": "fixture-live-client",
        "IFOOD_CLIENT_SECRET": "fixture-not-a-real-secret",
    }.items():
        monkeypatch.setattr(settings, name, value)

    class FakeClient:
        def __init__(self):
            self.calls = []
            self.error = None

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def ingest_items(self, merchant, items, **kwargs):
            self.calls.append((merchant, deepcopy(items), kwargs))
            if self.error:
                raise self.error
            return {
                "status_code": 202,
                "response": {"requestId": str(uuid4()), "private": "not-persisted"},
            }

    provider = FakeClient()
    monkeypatch.setattr(
        sync, "_client", lambda: pytest.fail("No real client in live unit tests")
    )

    def tick(now=START):
        api.db.commit()
        result = sync.poll_ifood_stock_once(
            client_factory=lambda: provider,
            session_factory=lambda: Session(api.engine),
            now=now,
        )
        api.db.expire_all()
        return result

    protected = {
        column.key: deepcopy(getattr(api.other, column.key))
        for column in api.other.__mapper__.columns
    }
    prices = {
        name: getattr(api.first, name)
        for name in ("preco_venda", "preco_app", "preco_ecommerce", "preco_ifood")
    }
    return SimpleNamespace(
        **vars(api),
        merchant=MERCHANT,
        config=config,
        link=link,
        confirmation=confirmation,
        provider=provider,
        protected=protected,
        prices=prices,
        tick=tick,
        real_client_factory=real_client_factory,
    )


def _never_db():
    pytest.fail("Guard must run before opening the database")


def _assert_protected(p):
    assert {
        column.key: getattr(p.other, column.key)
        for column in p.other.__mapper__.columns
    } == p.protected
    assert {name: getattr(p.first, name) for name in p.prices} == p.prices
    for merchant, items, kwargs in p.provider.calls:
        assert merchant == MERCHANT
        assert kwargs == {"method": "PATCH", "reset_catalog": False}
        assert items == [
            {"barcode": BARCODE, "inventory": {"stock": items[0]["inventory"]["stock"]}}
        ]


def test_live_opt_in_defaults_to_false():
    assert (
        settings.__class__.model_fields["IFOOD_STOCK_SYNC_LIVE_ENABLED"].default
        is False
    )


@pytest.mark.parametrize(
    "flag",
    [
        "IFOOD_STOCK_SYNC_LIVE_ENABLED",
        "IFOOD_STOCK_SYNC_POLLING_ENABLED",
        "IFOOD_CATALOG_WRITE_ENABLED",
    ],
)
def test_live_requires_each_opt_in_before_db(live, monkeypatch, flag):
    monkeypatch.setattr(settings, flag, False)
    assert sync.poll_ifood_stock_once(session_factory=_never_db)["status"] == "disabled"
    assert not live.provider.calls


def test_live_and_dev_flags_are_mutually_exclusive(live, monkeypatch):
    monkeypatch.setattr(settings, "IFOOD_STOCK_SYNC_DEV_ENABLED", True)
    assert (
        sync.poll_ifood_stock_once(session_factory=_never_db)["reason"]
        == "mode_conflict"
    )


@pytest.mark.parametrize(
    "runtime", ["development", "dev", "test", "local", "staging", "", "unknown"]
)
def test_live_only_accepts_production_runtime(live, monkeypatch, runtime):
    monkeypatch.setattr(settings, "ENVIRONMENT", runtime)
    for name in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.setenv(name, runtime)
    assert (
        sync.poll_ifood_stock_once(session_factory=_never_db)["reason"]
        == "production_only"
    )


@pytest.mark.parametrize("alias", ["APP_ENV", "ENV", "ENVIRONMENT"])
@pytest.mark.parametrize("runtime", ["development", "test", "staging", "unknown"])
def test_live_rejects_mixed_or_unknown_runtime_aliases(
    live, monkeypatch, alias, runtime
):
    monkeypatch.setenv(alias, runtime)
    assert (
        sync.poll_ifood_stock_once(session_factory=_never_db)["reason"]
        == "production_only"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://merchant-api.ifood.com.br",
        "https://merchant-api.ifood.com.br:443",
        "https://merchant-api.ifood.com.br.evil.invalid",
        "https://merchant-api.ifood.com.br@evil.invalid",
        "https://user:password@merchant-api.ifood.com.br",
        "http://127.0.0.1:9",
        "https://merchant-api.ifood.com.br/other",
        "https://merchant-api.ifood.com.br//",
        "https://merchant-api.ifood.com.br?next=external",
        "https://merchant-api.ifood.com.br#fragment",
    ],
)
def test_live_requires_official_exact_https_origin(live, monkeypatch, url):
    monkeypatch.setattr(settings, "IFOOD_API_BASE_URL", url)
    assert (
        sync.poll_ifood_stock_once(session_factory=_never_db)["reason"]
        == "provider_not_official"
    )
    assert not live.provider.calls


@pytest.mark.parametrize(
    "field,value",
    [
        ("IFOOD_STOCK_SYNC_TENANT_ID", str(uuid4())),
        ("IFOOD_STOCK_SYNC_MERCHANT_ID", str(uuid4())),
        ("IFOOD_STOCK_SYNC_PRODUCT_ID", 5868),
        ("IFOOD_STOCK_SYNC_SKU", "018631.1"),
        ("IFOOD_STOCK_SYNC_BARCODE", "4006381333931"),
    ],
)
def test_live_scope_is_fixed_before_db(live, monkeypatch, field, value):
    monkeypatch.setattr(settings, field, value)
    assert sync.poll_ifood_stock_once(session_factory=_never_db)["reason"] in {
        "scope_invalid",
        "live_scope_invalid",
    }


def test_live_baseline_and_stock_only_send_persist_real_mode_without_confirmation(live):
    p = live
    assert p.first.id == PRODUCT
    assert p.first.codigo == "227", p.first.codigo
    assert sync.product_identifier(p.first) == BARCODE
    assert p.db.query(sync.Produto).filter_by(id=PRODUCT).first() is not None
    result = p.tick()
    assert result["status"] == "unchanged", result
    assert p.db.query(State).one().provider_mode == "ifood_api"
    p.first.estoque_atual = 20
    assert p.tick()["status"] == "accepted"
    assert p.tick()["status"] == "unchanged"
    row = p.db.query(Submission).one()
    assert row.provider_mode == "ifood_api" and row.source == "auto_stock"
    assert row.fields == ["stock"] and row.http_status == 202
    assert p.db.query(Confirmation).count() == 1
    view = submission_view(row)
    assert view["provider_mode"] == "ifood_api"
    assert "simulador" not in view["message"].lower()
    state = sync.stock_sync_view(p.db, p.tenant, p.merchant, PRODUCT)
    assert (
        state["environment"] == "production" and state["provider_mode"] == "ifood_api"
    )
    assert state["external_confirmed"] is False
    _assert_protected(p)


def test_live_coalesces_latest_stock_and_never_changes_prices(live):
    p = live
    p.first.estoque_atual = 20
    assert p.tick()["sent_stock"] == 20
    p.first.estoque_atual = 19
    assert p.tick(START + timedelta(seconds=30))["status"] == "cooldown"
    p.first.estoque_atual = 18
    assert p.tick(LATER)["sent_stock"] == 18
    assert p.tick(LATER + timedelta(days=1))["status"] == "unchanged"
    assert len(p.provider.calls) == 2
    _assert_protected(p)


@pytest.mark.parametrize("status", [None, 500])
def test_live_unknown_failure_is_durable_without_blind_retry(live, status):
    p = live
    p.provider.error = IfoodClientError("private-no-persist", status_code=status)
    p.first.estoque_atual = 20
    assert p.tick()["status"] == "uncertain"
    assert p.tick(LATER + timedelta(days=1))["status"] == "uncertain"
    assert len(p.provider.calls) == 1
    row = p.db.query(Submission).one()
    assert row.provider_mode == "ifood_api" and "private" not in str(row.evidence)
    _assert_protected(p)


def test_live_rate_limit_retries_latest_stock_after_window(live):
    p = live
    p.provider.error = IfoodClientError("rate-limit", status_code=429)
    p.first.estoque_atual = 20
    assert p.tick()["status"] == "backoff"
    p.first.estoque_atual = 19
    assert p.tick(START + timedelta(seconds=30))["status"] == "backoff"
    p.provider.error = None
    assert p.tick(LATER)["sent_stock"] == 19
    assert len(p.provider.calls) == 2
    _assert_protected(p)


@pytest.mark.parametrize("change", ["sku", "barcode", "selection", "link", "merchant"])
def test_live_database_target_mismatch_cannot_publish_another_item(live, change):
    p = live
    if change == "sku":
        p.first.codigo = "018631.1"
    elif change == "barcode":
        p.first.codigo_barras = p.first.gtin_ean = "4006381333931"
    elif change == "selection":
        p.first.anunciar_ifood = False
    elif change == "link":
        p.link.mode = "new"
    else:
        p.config.merchant_id = str(uuid4())
    p.first.estoque_atual = 20
    assert p.tick()["status"] == "blocked"
    assert not p.provider.calls and p.db.query(Submission).count() == 0


def test_live_state_history_does_not_turn_into_simulator_when_flags_are_disabled(
    live, monkeypatch
):
    p = live
    p.first.estoque_atual = 20
    assert p.tick()["status"] == "accepted"
    monkeypatch.setattr(settings, "IFOOD_STOCK_SYNC_LIVE_ENABLED", False)
    state = sync.stock_sync_view(p.db, p.tenant, p.merchant, PRODUCT)
    assert not state["enabled"]
    assert (
        state["environment"] == "production" and state["provider_mode"] == "ifood_api"
    )
    assert submission_view(p.db.query(Submission).one())["provider_mode"] == "ifood_api"


def test_old_simulator_state_cannot_be_reused_as_live_acceptance(live):
    p = live
    state = State(
        tenant_id=p.tenant,
        merchant_id=MERCHANT,
        link_id=p.link.id,
        link_revision=1,
        provider_mode="local_simulator",
        desired_stock=21,
        last_accepted_stock=21,
        status="accepted",
        failure_count=0,
        reference_source="api_acceptance",
    )
    p.db.add(state)
    p.first.estoque_atual = 20
    assert p.tick()["status"] == "blocked"
    assert not p.provider.calls
    assert p.db.query(State).one().provider_mode == "local_simulator"


@pytest.mark.parametrize("credential", ["IFOOD_CLIENT_ID", "IFOOD_CLIENT_SECRET"])
@pytest.mark.parametrize("missing", [None, "", "  "])
def test_live_requires_both_credentials_without_opening_db(
    live, monkeypatch, credential, missing
):
    monkeypatch.setattr(settings, credential, missing)
    assert (
        sync.poll_ifood_stock_once(session_factory=_never_db)["reason"]
        == "credentials_missing"
    )


@pytest.mark.parametrize("runtime", ["prod", "production"])
def test_live_accepts_production_alias_and_single_trailing_slash(
    live, monkeypatch, runtime
):
    monkeypatch.setattr(settings, "ENVIRONMENT", runtime)
    monkeypatch.setattr(
        settings, "IFOOD_API_BASE_URL", "https://merchant-api.ifood.com.br/"
    )
    for name in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.setenv(name, runtime)
    assert live.tick()["status"] == "unchanged"
    assert sync.enabled_for(live.tenant, MERCHANT, PRODUCT)
    assert not sync.enabled_for(live.foreign, MERCHANT, PRODUCT)
    assert not sync.enabled_for(live.tenant, MERCHANT, live.other.id)


@pytest.mark.parametrize("baseline", ["missing", "absent", "inactive", "unknown_stock"])
def test_live_requires_human_active_item_and_known_stock_before_dispatch(
    live, baseline
):
    if baseline == "missing":
        live.db.delete(live.confirmation)
    elif baseline == "absent":
        live.confirmation.present = False
    elif baseline == "inactive":
        live.confirmation.portal_active = False
    else:
        live.confirmation.stock = None
    live.first.estoque_atual = 20
    result = live.tick()
    assert (
        result["status"] == "blocked"
        and result["reason"] == "initial_confirmation_required"
    )
    assert not live.provider.calls and live.db.query(Submission).count() == 0


def test_live_transport_does_not_follow_redirect_or_proxy_and_marks_uncertain(
    live, monkeypatch
):
    seen = []
    construction = []

    def handler(request):
        seen.append(request)
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(
                200, json={"accessToken": "fixture-token", "expiresIn": 3600}
            )
        return httpx.Response(
            302, headers={"Location": "https://attacker.invalid/capture"}
        )

    def client_constructor(**kwargs):
        construction.append(kwargs)
        return IfoodClient(**kwargs, transport=httpx.MockTransport(handler))

    monkeypatch.setenv("HTTPS_PROXY", "http://attacker.invalid:9999")
    monkeypatch.setattr(sync, "IfoodClient", client_constructor)
    live.first.estoque_atual = 20
    live.db.commit()
    result = sync.poll_ifood_stock_once(
        client_factory=lambda: live.real_client_factory(expected_mode="ifood_api"),
        session_factory=lambda: Session(live.engine),
        now=START,
    )
    assert result["status"] == "uncertain"
    assert live.tick(LATER)["status"] == "uncertain"
    row = live.db.query(Submission).one()
    assert row.http_status == 302 and row.status == "uncertain"
    assert construction[0]["trust_env"] is False
    assert 1 <= construction[0]["timeout_seconds"] <= 15
    assert len(seen) == 2
    assert all(request.url.host == "merchant-api.ifood.com.br" for request in seen)


def test_live_client_factory_fences_mode_change_before_constructing_transport(
    live, monkeypatch
):
    monkeypatch.setattr(
        sync,
        "IfoodClient",
        lambda **kwargs: pytest.fail("Mode fence must precede transport"),
    )
    with pytest.raises(IfoodClientError, match="diverge"):
        live.real_client_factory(expected_mode="local_simulator")
