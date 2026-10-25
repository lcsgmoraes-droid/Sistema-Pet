"""Conferencia do Portal com fila ativa: PostgreSQL descartavel, sem rede.

Exercita o mesmo lock da rota e o servico de confirmacao versionado. Cada
observacao e humana e append-only; nunca e recibo da API ou novo envio.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import re
import runpy
from threading import Barrier, Event

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from tests.integration.test_ifood_pdv_pilot_postgres import pg_engine  # noqa: F401
from tests.integration.test_ifood_stock_sync_postgres import (
    BARCODE,
    START,
    _assert_protected,
    _restricted_engine,
    _stock,
    _tick,
    stock_pg_engine,  # noqa: F401
    stock_pilot,  # noqa: F401
)


def _guard_schema(conn):
    assert (
        conn.exec_driver_sql("SELECT current_database()").scalar_one()
        == "ifood_pdv_test"
    )
    assert re.fullmatch(
        r"ifood_pdv_[a-f0-9]{32}",
        conn.exec_driver_sql("SELECT current_schema()").scalar_one(),
    )


def _observation_migration():
    matches = list(
        (Path(__file__).parents[2] / "alembic/versions").glob("zzzzx20261025a1*.py")
    )
    assert len(matches) == 1, "Expected the single Portal observation migration"
    return runpy.run_path(str(matches[0]))


@pytest.fixture(scope="module", autouse=True)
def observation_pg_migration(request):
    engine = request.getfixturevalue("stock_pg_engine")
    from app.ifood_catalog_models import IfoodCatalogConfirmation, IfoodCatalogLink

    with engine.begin() as conn:
        _guard_schema(conn)
        link = (
            conn.execute(
                select(IfoodCatalogLink.__table__).order_by(IfoodCatalogLink.id)
            )
            .mappings()
            .first()
        )
        assert link is not None
        conn.execute(
            IfoodCatalogConfirmation.__table__.insert().values(
                tenant_id=link["tenant_id"],
                link_id=link["id"],
                barcode=BARCODE,
                kind="portal",
                present=True,
                portal_active=False,
                price=0,
                stock=None,
                actor_id=link["portal_checked_by"],
                confirmed_at=START - timedelta(days=1),
            )
        )
        before = [
            dict(row)
            for row in conn.execute(
                select(IfoodCatalogConfirmation.__table__).order_by(
                    IfoodCatalogConfirmation.id
                )
            ).mappings()
        ]
        assert before and all(row["kind"] in {"link", "portal"} for row in before)
        # O metadata atual conhece observation. Reconstituir o check anterior
        # comprova que a migration e aplicada, sem tocar a evidencia existente.
        conn.exec_driver_sql(
            "ALTER TABLE ifood_catalog_confirmations DROP CONSTRAINT ck_ifood_catalog_confirmation_kind"
        )
        conn.exec_driver_sql(
            "ALTER TABLE ifood_catalog_confirmations ADD CONSTRAINT ck_ifood_catalog_confirmation_kind CHECK (kind IN ('link','portal'))"
        )
        with Operations.context(MigrationContext.configure(conn)):
            _observation_migration()["upgrade"]()
        after = [
            dict(row)
            for row in conn.execute(
                select(IfoodCatalogConfirmation.__table__).order_by(
                    IfoodCatalogConfirmation.id
                )
            ).mappings()
        ]
        assert after == before
        checks = {
            row["name"]: row["sqltext"]
            for row in inspect(conn).get_check_constraints(
                "ifood_catalog_confirmations"
            )
        }
        assert "observation" in checks["ck_ifood_catalog_confirmation_kind"]


@pytest.fixture
def observed_pilot(request, monkeypatch):
    from app.config import settings
    from app.integrations.ifood import catalog_pilot, stock_sync

    c = request.getfixturevalue("stock_pilot")
    monkeypatch.setattr(settings, "IFOOD_STOCK_SYNC_LIVE_ENABLED", False)
    monkeypatch.setattr(catalog_pilot, "now", lambda: START + timedelta(minutes=1))
    monkeypatch.setattr(
        stock_sync,
        "_client",
        lambda **_: pytest.fail("No real HTTP in Portal observation tests"),
    )
    return c


def _mapped(row):
    return {
        column.key: deepcopy(getattr(row, column.key))
        for column in row.__mapper__.columns
    }


def _evidence(c, engine=None):
    from app.ifood_catalog_models import (
        IfoodCatalogConfirmation as Confirmation,
        IfoodCatalogLink as Link,
        IfoodCatalogSubmission as Submission,
        IfoodStockSyncState as State,
    )
    from app.tenancy.context import tenant_context
    from app.tenancy.rls import sync_rls_tenant

    with tenant_context(c.tenant_id), Session(engine or c.engine) as db:
        sync_rls_tenant(db, c.tenant_id)
        return {
            "link": _mapped(
                db.query(Link).filter_by(tenant_id=c.tenant_id, id=c.link_id).one()
            ),
            "state": [
                _mapped(row)
                for row in db.query(State)
                .filter_by(tenant_id=c.tenant_id)
                .order_by(State.id)
            ],
            "submissions": [
                _mapped(row)
                for row in db.query(Submission)
                .filter_by(tenant_id=c.tenant_id)
                .order_by(Submission.id)
            ],
            "confirmations": [
                _mapped(row)
                for row in db.query(Confirmation)
                .filter_by(tenant_id=c.tenant_id)
                .order_by(Confirmation.id)
            ],
        }


def _publication(c, engine=None):
    from app.integrations.ifood import catalog_pilot
    from app.routes.ifood_catalog_pilot_routes import _state
    from app.tenancy.context import tenant_context
    from app.tenancy.rls import sync_rls_tenant

    with tenant_context(c.tenant_id), Session(engine or c.engine) as db:
        sync_rls_tenant(db, c.tenant_id)
        config, product = _state(db, c.tenant_id, c.product_id)
        return catalog_pilot.publication_view(
            db,
            c.tenant_id,
            config,
            product,
            can_edit=True,
            write_enabled=True,
            credentials=True,
        )


def _confirm(
    c,
    token,
    *,
    engine=None,
    present=True,
    active=True,
    stock=20,
    price="154.90",
    start_barrier=None,
):
    from app.integrations.ifood import catalog_pilot
    from app.routes.ifood_catalog_pilot_routes import ConfirmationBody, _state
    from app.tenancy.context import tenant_context
    from app.tenancy.rls import sync_rls_tenant

    if start_barrier:
        start_barrier.wait(timeout=10)
    with tenant_context(c.tenant_id), Session(engine or c.engine) as db:
        sync_rls_tenant(db, c.tenant_id)
        config, product = _state(db, c.tenant_id, c.product_id, lock=True)
        body = ConfirmationBody.model_validate(
            {
                "merchant_id": c.merchant_id,
                "barcode": BARCODE,
                "present": present,
                "portal_active": active,
                "stock": stock,
                "price": price,
                "confirmation_context_token": token,
            }
        )
        catalog_pilot.confirm_portal(
            db, c.tenant_id, config, product, body.model_dump(mode="python"), c.user_id
        )
        db.commit()
    return 200


def _token(c, engine=None):
    value = _publication(c, engine)["confirmation_context_token"]
    assert re.fullmatch(r"[0-9a-f]{64}", value)
    return value


def _accepted(c):
    _stock(c, 20)
    assert _tick(c)["status"] == "accepted"
    assert len(c.provider.calls) == 1


def _assert_receipt_only(before, after):
    assert after["link"] == before["link"]
    assert after["state"] == before["state"]
    assert after["submissions"] == before["submissions"]
    previous = {row["id"]: row for row in before["confirmations"]}
    assert all(
        row == previous[row["id"]]
        for row in after["confirmations"]
        if row["id"] in previous
    )
    added = [row for row in after["confirmations"] if row["id"] not in previous]
    assert len(added) == 1 and added[0]["kind"] == "observation"
    return added[0]


def test_receipt_after_202_preserves_history_and_existing_cooldown(observed_pilot):
    c = observed_pilot
    _accepted(c)
    before = _evidence(c)
    assert _publication(c)["capabilities"]["can_confirm"] is True
    assert _confirm(c, _token(c)) == 200
    observation = _assert_receipt_only(before, _evidence(c))
    assert observation["portal_active"] is True and observation["stock"] == 20
    assert _tick(c, 1)["status"] == "unchanged"
    _stock(c, 19)
    assert _tick(c, 2)["status"] == "cooldown"
    assert (
        _evidence(c)["state"][0]["next_attempt_at"]
        == before["state"][0]["next_attempt_at"]
    )
    assert _tick(c, 35)["sent_stock"] == 19
    assert len(c.provider.calls) == 2
    _assert_protected(c)


def test_local_stock_change_while_observing_does_not_erase_pending_delta(
    observed_pilot,
):
    c = observed_pilot
    _accepted(c)
    token = _token(c)
    _stock(c, 18)
    before = _evidence(c)
    assert _confirm(c, token, stock=20) == 200
    _assert_receipt_only(before, _evidence(c))
    assert _tick(c, 2)["status"] == "cooldown"
    assert _evidence(c)["state"][0]["desired_stock"] == 18
    assert _tick(c, 35)["sent_stock"] == 18
    assert len(c.provider.calls) == 2
    _assert_protected(c)


def test_confirmations_using_same_context_are_serialized_and_one_is_stale(
    observed_pilot,
):
    c = observed_pilot
    _accepted(c)
    before = _evidence(c)
    token = _token(c)
    barrier = Barrier(2)

    def confirm():
        try:
            return _confirm(c, token, start_barrier=barrier)
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            future.result(timeout=15)
            for future in [pool.submit(confirm), pool.submit(confirm)]
        ]
    assert sorted(results) == [200, 409]
    _assert_receipt_only(before, _evidence(c))
    assert len(c.provider.calls) == 1
    _assert_protected(c)


def test_new_dispatch_rejects_old_observation_and_confirmation_during_sending(
    observed_pilot,
):
    c = observed_pilot
    assert _tick(c)["status"] == "unchanged"
    token = _token(c)
    before = _evidence(c)
    _stock(c, 20)
    c.provider.entered, c.provider.release = Event(), Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        sending = pool.submit(_tick, c, 36)
        assert c.provider.entered.wait(timeout=15)
        try:
            assert _publication(c)["capabilities"]["can_confirm"] is False
            with pytest.raises(HTTPException) as failure:
                _confirm(c, token)
            assert failure.value.status_code == 409
        finally:
            c.provider.release.set()
        assert sending.result(timeout=15)["status"] == "accepted"
    with pytest.raises(HTTPException) as failure:
        _confirm(c, token)
    assert failure.value.status_code == 409
    assert _evidence(c)["confirmations"] == before["confirmations"]
    assert len(c.provider.calls) == 1
    assert _tick(c, 72)["status"] == "unchanged"
    _assert_protected(c)


@pytest.mark.parametrize("http_status", [None, 429])
def test_unknown_result_or_backoff_cannot_be_cleared_by_observation(
    observed_pilot, http_status
):
    from app.integrations.ifood.client import IfoodClientError

    c = observed_pilot
    _tick(c)
    token = _token(c)
    _stock(c, 20)

    def failed(*_, **__):
        raise IfoodClientError("Injected local failure", status_code=http_status)

    c.provider.ingest_items = failed
    assert _tick(c, 36)["status"] == ("backoff" if http_status == 429 else "uncertain")
    before = _evidence(c)
    assert _publication(c)["capabilities"]["can_confirm"] is False
    with pytest.raises(HTTPException) as failure:
        _confirm(c, token)
    assert failure.value.status_code == 409
    assert _evidence(c) == before
    assert _tick(c, 37)["status"] in {"backoff", "uncertain"}


@pytest.mark.parametrize(
    "present,active,stock", [(False, None, None), (True, False, 20), (True, None, None)]
)
def test_absent_inactive_or_unknown_observation_blocks_dispatch_without_reseeding(
    observed_pilot, present, active, stock
):
    c = observed_pilot
    _accepted(c)
    before = _evidence(c)
    _confirm(c, _token(c), present=present, active=active, stock=stock, price=None)
    observation = _assert_receipt_only(before, _evidence(c))
    assert observation["present"] is present and observation["portal_active"] is active
    _stock(c, 19)
    assert _tick(c, 36)["status"] == "blocked"
    assert _evidence(c)["state"] == before["state"]
    assert len(c.provider.calls) == 1
    _confirm(c, _token(c), present=True, active=True, stock=20)
    assert _tick(c, 36)["sent_stock"] == 19
    assert len(c.provider.calls) == 2
    _assert_protected(c)


def test_observed_zero_is_stored_as_zero_and_does_not_rewrite_accepted_stock(
    observed_pilot,
):
    c = observed_pilot
    _accepted(c)
    before = _evidence(c)
    _confirm(c, _token(c), stock=0, price=0)
    observation = _assert_receipt_only(before, _evidence(c))
    assert observation["stock"] == 0 and observation["price"] == 0
    assert _tick(c, 36)["status"] == "unchanged"
    assert _evidence(c)["state"][0]["last_accepted_stock"] == 20
    assert len(c.provider.calls) == 1
    _assert_protected(c)


def test_real_rls_isolates_observation_and_rejects_foreign_context(observed_pilot):
    from app.ifood_catalog_models import IfoodCatalogConfirmation as Confirmation
    from app.routes.ifood_catalog_pilot_routes import _state
    from app.tenancy.context import tenant_context
    from app.tenancy.rls import sync_rls_tenant

    c = observed_pilot
    _accepted(c)
    with _restricted_engine(c) as restricted:
        with restricted.connect() as conn:
            role = conn.exec_driver_sql("SELECT current_user").scalar_one()
        assert re.fullmatch(r"ifood_stock_role_[a-f0-9]{32}", role)
        with c.engine.begin() as conn:
            _guard_schema(conn)
            conn.exec_driver_sql(
                f'GRANT INSERT ON ifood_catalog_confirmations TO "{role}"'
            )
            conn.exec_driver_sql(f'GRANT UPDATE ON ifood_catalog_links TO "{role}"')
        before = _evidence(c, restricted)
        _confirm(c, _token(c, restricted), engine=restricted)
        _assert_receipt_only(before, _evidence(c, restricted))
        with tenant_context(c.other_tenant), Session(restricted) as db:
            sync_rls_tenant(db, c.other_tenant)
            assert (
                db.query(Confirmation).filter(Confirmation.link_id == c.link_id).count()
                == 0
            )
            with pytest.raises(HTTPException) as failure:
                _state(db, c.other_tenant, c.product_id, lock=True)
            assert failure.value.status_code == 404
        with restricted.connect() as conn:
            flags = conn.exec_driver_sql(
                "SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='ifood_catalog_confirmations'::regclass"
            ).one()
            assert all(flags)
    _assert_protected(c)


def test_downgrade_refuses_to_discard_observation_history(observed_pilot):
    c = observed_pilot
    _accepted(c)
    _confirm(c, _token(c))
    before = _evidence(c)
    with c.engine.begin() as conn:
        _guard_schema(conn)
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError, match="observa|historico"):
                _observation_migration()["downgrade"]()
        checks = {
            row["name"]: row["sqltext"]
            for row in inspect(conn).get_check_constraints(
                "ifood_catalog_confirmations"
            )
        }
        assert "observation" in checks["ck_ifood_catalog_confirmation_kind"]
    assert _evidence(c) == before
