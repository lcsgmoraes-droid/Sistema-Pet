from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.ifood_financial_models import IfoodFinancialEvent, IfoodFinancialSnapshot
from app.ifood_integration_models import IfoodMerchantConfig
from app.ifood_payout_models import IfoodPayoutSnapshot, IfoodReconciliationJob
from app.integrations.ifood.financial import IfoodFinancialError
from app.integrations.ifood.client import IfoodClientError
from app.integrations.ifood.payouts import (
    get_payout_report,
    import_settlements,
    import_statement,
    payout_period,
)
from app.integrations.ifood.reconciliation import (
    advance_reconciliation,
    get_reconciliation_status,
)
from app.tenancy.context import tenant_context

MERCHANT = "184bad64-04a8-4877-9789-2e246b3ae4e4"
BEGIN, END = "2025-03-01", "2025-03-02"


@pytest.fixture
def scope():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            m.__table__
            for m in (
                IfoodMerchantConfig,
                IfoodPayoutSnapshot,
                IfoodReconciliationJob,
                IfoodFinancialSnapshot,
                IfoodFinancialEvent,
            )
        ],
    )
    tenant = uuid4()
    with Session(engine) as db, tenant_context(tenant):
        db.add(
            IfoodMerchantConfig(tenant_id=tenant, merchant_id=MERCHANT, active=False)
        )
        db.commit()
        yield db, tenant
    engine.dispose()


def provider(amount="91", **changes):
    title = dict(
        id="110825088",
        type="REPASSE",
        amount=amount,
        status="SUCCEED",
        paymentDate="2025-03-07",
        accountDetails={"secret": "must disappear"},
    )
    title.update(changes)
    return dict(
        merchantId=MERCHANT,
        beginDate=BEGIN,
        endDate=END,
        balance="80",
        settlements=[
            dict(
                startDateCalculation=BEGIN, endDateCalculation=END, closingItems=[title]
            )
        ],
    )


def row(amount="91", **changes):
    result = dict(
        position=1,
        title_id="110825088",
        balance_id="80000",
        amount=amount,
        has_transfer_impact=True,
        transaction_amount="91",
        transaction_open=False,
        order_id=None,
        period_begin=BEGIN,
        period_end=END,
        expected_payment_date="2025-03-07",
    )
    result.update(changes)
    return result


def statement(scope, *rows, competence="2025-03", source="ifood"):
    db, tenant = scope
    return import_statement(
        db,
        tenant,
        MERCHANT,
        competence,
        dict(
            merchant_id=MERCHANT,
            competence=competence,
            rows=list(rows),
            row_count=len(rows),
        ),
        1,
        source=source,
    )


def events(scope, amount="91", begin=BEGIN, end=END, source="ifood_financial_events"):
    db, tenant = scope
    snapshot = IfoodFinancialSnapshot(
        tenant_id=tenant,
        merchant_id=MERCHANT,
        mode="homologation",
        begin_date=date.fromisoformat(begin),
        end_date=date.fromisoformat(end),
        revision=1,
        active=True,
        source=source,
        payload_hash="x" * 64,
        page_count=1,
        event_count=1,
        actor_id=1,
    )
    db.add(snapshot)
    db.flush()
    db.add(
        IfoodFinancialEvent(
            tenant_id=tenant,
            snapshot_id=snapshot.id,
            position=1,
            order_id=None,
            name="ORDER_PAYMENT",
            trigger="ORDER_CONCLUDED",
            amount=Decimal(amount),
            has_transfer_impact=True,
            evidence={"period": {"beginDate": begin, "endDate": end}},
        )
    )
    db.flush()


def imported(scope, data=None, **kwargs):
    db, tenant = scope
    return import_settlements(
        db, tenant, MERCHANT, BEGIN, END, data or provider(), 1, **kwargs
    )


def test_exact_title_reconciles_all_three_totals_and_period_but_never_bank(scope):
    statement(scope, row("100"), row("-9", position=2))
    events(scope)
    report = imported(scope)
    title = report["titles"][0]
    assert title["reconciliation_status"] == "matched"
    assert (
        title["statement_amount"]
        == title["statement_lines_sum"]
        == title["events_period_sum"]
        == "91.00"
    )
    assert title["bank_status"] == "not_checked"
    assert title["link_method"] == "legacy_title"
    assert report["reported_balance"] == "80.00"  # Not the sum of title amounts.
    assert "accountDetails" not in str(
        scope[0].query(IfoodPayoutSnapshot).filter_by(kind="settlements").one().evidence
    )


def test_same_balance_id_is_never_assumed_to_be_title(scope):
    statement(scope, row(title_id=None, balance_id="110825088"))
    events(scope)
    report = imported(scope)
    assert report["titles"][0]["reconciliation_status"] == "pending"
    assert report["titles"][0]["link_method"] is None
    assert report["unmatched_balances"][0]["balance_id"] == "110825088"


@pytest.mark.parametrize(
    "change",
    [
        dict(transaction_amount=None),
        dict(transaction_open=True),
        dict(transaction_amount="90"),
    ],
)
def test_open_missing_or_conflicting_transaction_total_never_reconciles(scope, change):
    statement(scope, row(**change))
    events(scope)
    assert imported(scope)["titles"][0]["reconciliation_status"] != "matched"


def test_cent_difference_is_not_silently_tolerated(scope):
    statement(scope, row("90.99"))
    events(scope, "90.99")
    title = imported(scope)["titles"][0]
    assert title["reconciliation_status"] == "different"
    assert title["difference"] == "0.01"


def test_period_event_difference_blocks_even_matching_title_totals(scope):
    statement(scope, row())
    events(scope, "90")
    title = imported(scope)["titles"][0]
    assert title["reconciliation_status"] == "pending"
    assert any("Eventos e arquivo" in issue for issue in title["issues"])


def test_subperiod_event_is_never_dropped_from_complete_window(scope):
    statement(scope, row("100", transaction_amount="100"))
    events(scope, "100")
    db, tenant = scope
    snapshot = db.query(IfoodFinancialSnapshot).one()
    db.add(
        IfoodFinancialEvent(
            tenant_id=tenant,
            snapshot_id=snapshot.id,
            position=2,
            order_id=None,
            name="ORDER_COMMISSION",
            trigger="ORDER_CONCLUDED",
            amount=Decimal("-10"),
            has_transfer_impact=True,
            evidence={"period": {"beginDate": END, "endDate": END}},
        )
    )
    db.flush()
    title = imported(scope, provider("100"))["titles"][0]
    assert title["events_period_sum"] == "90.00"
    assert title["event_count"] == 2
    assert title["reconciliation_status"] == "pending"


def test_missing_exact_event_window_is_pending_not_zero(scope):
    statement(scope, row())
    title = imported(scope)["titles"][0]
    assert title["events_period_sum"] is None
    assert title["reconciliation_status"] == "pending"


def test_synthetic_statement_cannot_prove_official_title(scope):
    statement(scope, row(), source="synthetic")
    events(scope)
    assert imported(scope)["titles"][0]["link_method"] is None


def test_payout_without_import_is_distinct_from_empty_provider_response(scope):
    db, tenant = scope
    assert not get_payout_report(db, tenant, MERCHANT, BEGIN, END)["imported"]
    payload = provider()
    payload["settlements"] = []
    report = imported(scope, payload)
    assert report["imported"] and not report["titles"]
    assert "sem títulos" in report["warnings"][-1]


def test_different_title_types_are_totalled_separately(scope):
    payload = provider()
    payload["settlements"][0]["closingItems"].append(
        dict(id="110825091", type="REGISTRO_RECEBIVEIS", amount="-11", status="SUCCEED")
    )
    report = imported(scope, payload)
    assert report["summary"]["totals_by_type"] == {
        "REPASSE": "91.00",
        "REGISTRO_RECEBIVEIS": "-11.00",
    }
    assert all(t["bank_status"] == "not_checked" for t in report["titles"])


def test_complete_same_window_refresh_keeps_versions_without_duplicating(scope):
    db, tenant = scope
    imported(scope)
    imported(scope)
    assert db.query(IfoodPayoutSnapshot).count() == 1
    imported(scope, provider("90"))
    records = db.query(IfoodPayoutSnapshot).order_by(IfoodPayoutSnapshot.revision).all()
    assert [r.active for r in records] == [False, True]
    assert (
        get_payout_report(db, tenant, MERCHANT, BEGIN, END)["summary"]["titles_count"]
        == 1
    )


@pytest.mark.parametrize(
    "mutation", ["merchant", "date", "duplicate", "missing_amount"]
)
def test_invalid_refresh_preserves_previous_evidence(scope, mutation):
    db, tenant = scope
    imported(scope)
    payload = provider()
    if mutation == "merchant":
        payload["merchantId"] = str(uuid4())
    elif mutation == "date":
        payload["endDate"] = "2025-03-03"
    elif mutation == "duplicate":
        payload["settlements"][0]["closingItems"] *= 2
    else:
        payload["settlements"][0]["closingItems"][0]["amount"] = None
    with pytest.raises(IfoodFinancialError):
        imported(scope, payload)
    assert (
        get_payout_report(db, tenant, MERCHANT, BEGIN, END)["titles"][0]["amount"]
        == "91.00"
    )


def test_multiple_month_apuration_requires_all_month_files(scope):
    db, tenant = scope
    begin, end = "2025-02-24", "2025-03-02"
    statement(scope, row(period_begin=begin, period_end=end))
    payload = provider()
    payload["beginDate"], payload["endDate"] = begin, end
    group = payload["settlements"][0]
    group["startDateCalculation"], group["endDateCalculation"] = begin, end
    events(scope, begin=begin, end=end)
    report = import_settlements(db, tenant, MERCHANT, begin, end, payload, 1)
    assert any("competências" in issue for issue in report["titles"][0]["issues"])
    statement(scope, competence="2025-02")
    assert (
        get_payout_report(db, tenant, MERCHANT, begin, end)["titles"][0][
            "reconciliation_status"
        ]
        == "matched"
    )


def test_two_titles_in_same_period_compare_events_once_at_period_grain(scope):
    statement(
        scope,
        row("50", transaction_amount="50"),
        row("41", position=2, title_id="second", transaction_amount="41"),
    )
    events(scope)
    payload = provider("50")
    payload["settlements"][0]["closingItems"].append(
        dict(id="second", type="REPASSE", amount="41", status="SUCCEED")
    )
    report = imported(scope, payload)
    assert report["summary"]["matched_titles"] == 2
    assert [t["events_period_sum"] for t in report["titles"]] == ["91.00", "91.00"]


def test_tenant_mode_and_period_guards(scope):
    db, tenant = scope
    for kwargs in (dict(mode="production"), dict(basis="wrong")):
        with pytest.raises(IfoodFinancialError):
            imported(scope, **kwargs)
    with pytest.raises(IfoodFinancialError):
        get_payout_report(db, uuid4(), MERCHANT, BEGIN, END)
    with pytest.raises(IfoodFinancialError):
        payout_period("2025-01-01", "2025-04-01")


class ProviderJob:
    def __init__(self):
        self.created = 0
        self.checked = 0
        self.status = "enqueue"

    def create_reconciliation(self, merchant, competence):
        self.created += 1
        return dict(
            merchant_id=merchant,
            competence=competence,
            request_id="request-1",
            status="created",
        )

    def get_reconciliation(self, merchant, request, competence):
        self.checked += 1
        return dict(
            merchant_id=merchant,
            competence=competence,
            request_id=request,
            status=self.status,
        )


def test_request_reuses_id_honors_backoff_and_get_status_never_calls_provider(scope):
    db, tenant = scope
    client = ProviderJob()
    now = datetime(2025, 3, 4, tzinfo=timezone.utc)

    def call(at):
        return advance_reconciliation(
            db, tenant, MERCHANT, "2025-03", 1, client, now=at
        )

    assert call(now)["job"]["status"] == "created"
    assert call(now)["job"]["next_retry_after_seconds"] == 5
    assert client.created == 1 and client.checked == 0
    assert get_reconciliation_status(db, tenant, MERCHANT, "2025-03")["job"] is not None
    assert call(now + timedelta(seconds=5))["job"]["status"] == "enqueue"
    call(now + timedelta(seconds=6))
    assert client.created == client.checked == 1
    client.status = "error"
    assert call(now + timedelta(seconds=20))["job"]["status"] == "error"
    call(now + timedelta(hours=1))
    assert client.created == 1 and client.checked == 2


def test_first_conflict_without_id_is_honest_pending_not_new_request_loop(scope):
    db, tenant = scope
    client = ProviderJob()

    def conflict(merchant, competence):
        client.created += 1
        return dict(
            merchant_id=merchant,
            competence=competence,
            request_id=None,
            status="conflict",
        )

    client.create_reconciliation = conflict
    now = datetime.now(timezone.utc)
    result = advance_reconciliation(db, tenant, MERCHANT, "2025-03", 1, client, now=now)
    assert result["job"]["status"] == "conflict" and not result["imported"]
    advance_reconciliation(
        db, tenant, MERCHANT, "2025-03", 1, client, now=now + timedelta(hours=1)
    )
    assert client.created == 1 and client.checked == 0


def test_statement_rejects_wrong_scope_without_writing(scope):
    db, tenant = scope
    with pytest.raises(IfoodFinancialError):
        import_statement(
            db,
            tenant,
            MERCHANT,
            "2025-03",
            dict(merchant_id=str(uuid4()), competence="2025-03", rows=[], row_count=0),
            1,
        )
    assert db.query(IfoodPayoutSnapshot).count() == 0


@pytest.mark.parametrize("sub_amount", ["-10", "0"])
def test_subperiod_events_are_never_dropped_to_manufacture_a_match(scope, sub_amount):
    db, tenant = scope
    statement(scope, row("100", transaction_amount="100"))
    events(scope, "100")
    snapshot = db.query(IfoodFinancialSnapshot).one()
    snapshot.event_count = 2
    db.add(
        IfoodFinancialEvent(
            tenant_id=tenant,
            snapshot_id=snapshot.id,
            position=2,
            order_id=None,
            name="ORDER_COMMISSION",
            trigger="ORDER_CONCLUDED",
            amount=Decimal(sub_amount),
            has_transfer_impact=True,
            evidence={"period": {"beginDate": END, "endDate": END}},
        )
    )
    db.flush()
    title = imported(scope, provider("100"))["titles"][0]
    assert title["event_count"] == 2
    assert title["events_period_sum"] == ("90.00" if sub_amount == "-10" else "100.00")
    assert title["reconciliation_status"] == "pending"
    assert any("subperíodos" in issue for issue in title["issues"])


def test_consolidated_other_merchant_is_rejected_by_persistence_service(scope):
    db, _ = scope
    payload = provider()
    payload["consolidatedMerchants"] = [MERCHANT, str(uuid4())]
    with pytest.raises(IfoodFinancialError):
        imported(scope, payload)
    assert db.query(IfoodPayoutSnapshot).count() == 0


def test_flat_title_cannot_match_an_apuration_outside_requested_calculation_period(
    scope,
):
    statement(
        scope,
        row(period_begin="2025-02-01", period_end="2025-02-02"),
        competence="2025-02",
    )
    events(scope, begin="2025-02-01", end="2025-02-02")
    payload = provider()
    payload["settlements"] = payload["settlements"][0]["closingItems"]
    title = imported(scope, payload)["titles"][0]
    assert title["statement_lines_sum"] == title["events_period_sum"] == "91.00"
    assert title["reconciliation_status"] == "pending"
    assert any("fora da consulta" in issue for issue in title["issues"])


def test_moved_payment_date_remains_pending_despite_identical_title_and_amount(scope):
    statement(scope, row(expected_payment_date="2025-03-06"))
    events(scope)
    title = imported(scope)["titles"][0]
    assert title["statement_amount"] == title["events_period_sum"] == "91.00"
    assert title["reconciliation_status"] == "pending"
    assert any("Data de pagamento" in issue for issue in title["issues"])


class ProcessedProvider(ProviderJob):
    def __init__(self, failure=None):
        super().__init__()
        self.failure = failure
        self.downloaded = 0

    def get_reconciliation(self, merchant, request, competence):
        self.checked += 1
        if self.failure == "get429":
            raise IfoodClientError("private-provider-detail", status_code=429)
        return dict(
            merchant_id=merchant,
            competence=competence,
            request_id=request,
            status="processed",
            download_url="https://private-signed-url.example.test/file",
        )

    def download_statement(self, _url):
        self.downloaded += 1
        if self.failure == "download":
            raise IfoodClientError("private-signed-url must not leak")
        if self.failure == "parse":
            return b"invalid csv"
        return (
            "competencia;loja_id;valor;impacto_no_repasse;titulo;valor_transacao;data_apuracao_inicio;data_apuracao_fim\n"
            f"2025-03;{MERCHANT};91;SIM;110825088;91;{BEGIN};{END}\n"
        ).encode()


@pytest.mark.parametrize("failure", ["get429", "download", "parse"])
def test_failed_processed_job_persists_backoff_keeps_previous_evidence_and_reuses_request(
    scope, failure
):
    db, tenant = scope
    statement(scope, row("90", transaction_amount="90"))
    previous_id = db.query(IfoodPayoutSnapshot).one().id
    client = ProcessedProvider(failure)
    now = datetime(2025, 3, 4, tzinfo=timezone.utc)

    def call(at):
        result = advance_reconciliation(
            db, tenant, MERCHANT, "2025-03", 1, client, now=at
        )
        db.commit()
        return result

    call(now)
    failed = call(now + timedelta(seconds=5))
    assert failed["job"]["status"] == "created" and not failed["imported"]
    assert failed["job"]["next_retry_after_seconds"] >= (
        60 if failure == "get429" else 10
    )
    assert "preservada" in failed["job"]["last_error"]
    assert "private" not in failed["job"]["last_error"]
    assert db.query(IfoodPayoutSnapshot).one().id == previous_id
    assert db.query(IfoodPayoutSnapshot).one().evidence["rows"][0]["amount"] == "90.00"
    calls = (client.created, client.checked, client.downloaded)
    call(now + timedelta(seconds=6))
    assert (client.created, client.checked, client.downloaded) == calls
    assert db.query(IfoodReconciliationJob).one().request_id == "request-1"
    client.failure = None
    completed = call(now + timedelta(seconds=66))
    assert completed["imported"] and completed["job"]["status"] == "processed"
    assert client.created == 1
    assert (
        db.query(IfoodPayoutSnapshot)
        .filter_by(active=True)
        .one()
        .evidence["rows"][0]["amount"]
        == "91.00"
    )


def test_completed_file_is_cached_without_new_request_download_or_duplicate_import(
    scope,
):
    db, tenant = scope
    client = ProcessedProvider()
    now = datetime(2025, 3, 4, tzinfo=timezone.utc)
    advance_reconciliation(db, tenant, MERCHANT, "2025-03", 1, client, now=now)
    result = advance_reconciliation(
        db, tenant, MERCHANT, "2025-03", 1, client, now=now + timedelta(seconds=5)
    )
    assert (
        result["imported"]
        and client.created == client.checked == client.downloaded == 1
    )
    repeat = advance_reconciliation(
        db, tenant, MERCHANT, "2025-03", 1, client, now=now + timedelta(days=1)
    )
    assert (
        repeat["imported"]
        and client.created == client.checked == client.downloaded == 1
    )
    assert db.query(IfoodPayoutSnapshot).filter_by(kind="statement").count() == 1


def test_first_request_failure_is_cached_before_repeating_post(scope):
    db, tenant = scope
    client = ProviderJob()

    def failed_create(_merchant, _competence):
        client.created += 1
        raise IfoodClientError("private-first-request", status_code=429)

    client.create_reconciliation = failed_create
    now = datetime(2025, 3, 4, tzinfo=timezone.utc)
    result = advance_reconciliation(db, tenant, MERCHANT, "2025-03", 1, client, now=now)
    assert result["job"]["next_retry_after_seconds"] >= 60
    assert not result["imported"]
    db.commit()
    advance_reconciliation(
        db, tenant, MERCHANT, "2025-03", 1, client, now=now + timedelta(seconds=1)
    )
    assert client.created == 1
