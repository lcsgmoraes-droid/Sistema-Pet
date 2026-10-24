from decimal import Decimal
from pathlib import Path
import runpy
from types import SimpleNamespace
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.ifood_financial_models import (
    IfoodFinancialEvent,
    IfoodFinancialOrderCosts,
    IfoodFinancialSnapshot,
)
from app.ifood_integration_models import IfoodMerchantConfig
from app.integrations.ifood.financial import (
    IfoodFinancialError,
    get_financial_report,
    import_financial_pages,
    record_order_costs,
)
from app.tenancy.context import tenant_context

MERCHANT = "184bad64-04a8-4877-9789-2e246b3ae4e4"
ORDER = "003f1a11-63b5-45c6-a956-e6423f8a06ca"
BEGIN, END = "2025-03-01", "2025-03-02"


def financial_event(name="ORDER_PAYMENT", value="91.00", **changes):
    result = {
        "name": name,
        "description": "MARKETPLACE_PAYMENT",
        "product": "IFOOD",
        "trigger": "SALE_CONCLUDED",
        "competence": "2025-03",
        "dateTime": "2025-03-02T03:07:10Z",
        "period": {"beginDate": BEGIN, "endDate": END},
        "reference": {
            "type": "ORDER",
            "id": ORDER,
            "date": "2025-03-01T22:07:10.773670Z",
        },
        "hasTransferImpact": True,
        "amount": {"value": value},
        "receiver": {
            "businessId": MERCHANT,
            "businessType": "MERCHANT",
            "businessDocument": "00011122233344",
        },
        "payment": {"method": "PIX", "liability": "MERCHANT"},
    }
    result.update(changes)
    return result


def test_homologation_human_charge_label_is_preserved_but_not_classified(db):
    tenant = store(db)
    report = imported(
        db,
        tenant,
        financial_event(
            "Cobrança Pacote Anúncios",
            "-12",
            description="Pacote de anúncios",
            trigger="SINGLE_OCCURRENCE",
            reference=None,
        ),
    )
    assert report["unallocated_events"][0]["name"] == "Cobrança Pacote Anúncios"
    assert report["unallocated_events"][0]["amount"] == "-12.00"
    assert report["summary"]["transfer_impact"] == "-12.00"
    assert report["summary"]["unallocated_events"] == 1


def test_observed_order_concluded_trigger_is_recognized_without_changing_unknown_guards(
    db,
):
    tenant = store(db)
    imported(
        db,
        tenant,
        *[
            financial_event(name, value, trigger="ORDER_CONCLUDED")
            for name, value in (
                ("ORDER_PAYMENT", "96"),
                ("ORDER_COMMISSION", "-6"),
                ("PAYMENT_TRANSACTION_FEE", "-3"),
            )
        ],
    )
    result = costs(db, tenant, revenue="100", cmv="60", tax="4", other_costs="1")
    assert result["contribution"]["calculated"]
    assert result["contribution"]["amount"] == "26.00"


@pytest.mark.parametrize("label", ["\nunsafe", "x" * 101, "", "  "])
def test_event_labels_reject_controls_empty_and_overlong_values(db, label):
    tenant = store(db)
    with pytest.raises(IfoodFinancialError):
        imported(db, tenant, financial_event(label))


def pages(*events, size=100):
    chunks = [
        events[index : index + size] for index in range(0, len(events), size)
    ] or [[]]
    return [
        {
            "page": index + 1,
            "size": size,
            "hasNextPage": index < len(chunks) - 1,
            "financialEvents": list(chunk),
        }
        for index, chunk in enumerate(chunks)
    ]


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            IfoodMerchantConfig.__table__,
            IfoodFinancialSnapshot.__table__,
            IfoodFinancialEvent.__table__,
            IfoodFinancialOrderCosts.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def store(db, *, merchant=MERCHANT):
    tenant = uuid4()
    with tenant_context(tenant):
        db.add(
            IfoodMerchantConfig(tenant_id=tenant, merchant_id=merchant, active=False)
        )
        db.commit()
    return tenant


def imported(db, tenant, *events, merchant=MERCHANT, begin=BEGIN, end=END, **kwargs):
    with tenant_context(tenant):
        result = import_financial_pages(
            db,
            tenant,
            merchant,
            begin,
            end,
            pages(*events),
            actor_id=7,
            source="synthetic",
            **kwargs,
        )
        db.commit()
        return result


def costs(db, tenant, *, order=ORDER, merchant=MERCHANT, **values):
    data = {
        "revenue": "96.00",
        "cmv": "60.00",
        "tax": "4.00",
        "other_costs": "1.00",
        "source_note": "Comprovantes ficticios da venda em DEV",
        **values,
    }
    with tenant_context(tenant):
        result = record_order_costs(db, tenant, merchant, order, data, actor_id=9)
        db.commit()
        return result


def report(db, tenant, *, merchant=MERCHANT, begin=BEGIN, end=END):
    with tenant_context(tenant):
        return get_financial_report(db, tenant, merchant, begin, end)


def test_actual_charges_are_separate_from_receipts_subsidies_and_transfer(db):
    tenant = store(db)
    imported(
        db,
        tenant,
        financial_event(),
        financial_event("IFOOD_SUBSIDY", "5.00"),
        financial_event("STORE_SUBSIDY", "-5.00", hasTransferImpact=False),
        financial_event(
            "ORDER_COMMISSION",
            "-11.52",
            billing={"baseValue": "96", "feePercentage": "12"},
        ),
        financial_event("PAYMENT_TRANSACTION_FEE", "-3.07"),
    )
    result = costs(db, tenant)
    assert result["contribution"] == {
        "calculated": True,
        "amount": "16.41",
        "percent": "17.09",
        "label": "Contribuição com custos informados",
        "missing": [],
    }
    final = report(db, tenant)
    assert final["summary"] == {
        "order_count": 1,
        "event_count": 5,
        "registered_payments": "91.00",
        "ifood_subsidy": "5.00",
        "store_subsidy": "-5.00",
        "fees": "-14.59",
        "transfer_impact": "81.41",
        "unallocated_events": 0,
        "pending_orders": 0,
    }
    assert final["metadata"]["source"] == "synthetic"
    assert final["orders"][0]["manual_costs"]["actor_id"] == 9
    assert final["orders"][0]["events"][0]["date_time"] == "2025-03-02T03:07:10Z"
    assert "sintéticos" in " ".join(final["warnings"])


def test_direct_store_payment_is_receipt_without_transfer_or_double_fee(db):
    tenant = store(db)
    imported(
        db,
        tenant,
        financial_event(value="100", hasTransferImpact=False),
        financial_event("ORDER_COMMISSION", "-12"),
        financial_event("PAYMENT_TRANSACTION_FEE", "0"),
    )
    result = costs(db, tenant, revenue="100", cmv="40", tax="0", other_costs="0")
    assert result["contribution"]["amount"] == "48.00"
    totals = report(db, tenant)["summary"]
    assert totals["registered_payments"] == "100.00"
    assert totals["transfer_impact"] == "-12.00"
    assert totals["fees"] == "-12.00"


def test_identical_fees_and_credits_survive_by_position_and_reimport_does_not_double(
    db,
):
    tenant = store(db)
    entries = [
        financial_event(),
        financial_event("ORDER_COMMISSION", "-1.11"),
        financial_event("ORDER_COMMISSION", "-1.11"),
        financial_event("ORDER_COMMISSION", "1.11"),
    ]
    first = imported(db, tenant, *entries)
    second = imported(db, tenant, *entries)
    assert first["summary"] == second["summary"]
    assert second["summary"]["event_count"] == 4
    assert second["summary"]["fees"] == "-1.11"
    assert [e["position"] for e in second["orders"][0]["events"]] == [1, 2, 3, 4]
    assert second["metadata"]["revision"] == 2
    with tenant_context(tenant):
        snapshots = (
            db.query(IfoodFinancialSnapshot)
            .order_by(IfoodFinancialSnapshot.revision)
            .all()
        )
        assert [s.active for s in snapshots] == [False, True]
        assert db.query(IfoodFinancialEvent).count() == 8


def test_two_tenants_and_merchants_keep_orders_costs_and_reports_private(db):
    first = store(db)
    merchant_b = str(uuid4())
    second = store(db, merchant=merchant_b)
    imported(db, first, financial_event())
    imported(
        db,
        second,
        financial_event(
            value="12", receiver={"businessId": merchant_b, "businessType": "MERCHANT"}
        ),
        merchant=merchant_b,
    )
    costs(db, first)
    assert report(db, first)["summary"]["registered_payments"] == "91.00"
    other = report(db, second, merchant=merchant_b)
    assert other["summary"]["registered_payments"] == "12.00"
    assert other["orders"][0]["manual_costs"] is None
    with tenant_context(first), pytest.raises(IfoodFinancialError) as caught:
        get_financial_report(db, second, merchant_b, BEGIN, END)
    assert caught.value.status_code == 403


def test_new_merchant_binding_hides_old_snapshots_and_costs(db):
    tenant = store(db)
    imported(db, tenant, financial_event())
    costs(db, tenant)
    new_merchant = str(uuid4())
    with tenant_context(tenant):
        db.query(IfoodMerchantConfig).one().merchant_id = new_merchant
        db.commit()
    empty = report(db, tenant, merchant=new_merchant)
    assert empty["imported"] is False
    assert empty["orders"] == [] and empty["summary"]["fees"] is None
    with pytest.raises(IfoodFinancialError):
        report(db, tenant)


def test_overlap_rejected_while_exact_window_replacement_is_allowed(db):
    tenant = store(db)
    original = imported(db, tenant, financial_event())
    with pytest.raises(IfoodFinancialError) as caught:
        imported(
            db,
            tenant,
            financial_event(period={"beginDate": END, "endDate": "2025-03-03"}),
            begin=END,
            end="2025-03-03",
        )
    assert caught.value.status_code == 409
    assert (
        report(db, tenant)["metadata"]["snapshot_id"]
        == original["metadata"]["snapshot_id"]
    )
    updated = imported(db, tenant, financial_event(value="92"))
    assert updated["summary"]["registered_payments"] == "92.00"


@pytest.mark.parametrize(
    "invalid",
    [
        [{"page": 1, "size": 100, "hasNextPage": True, "financialEvents": []}],
        [{"page": 2, "size": 100, "hasNextPage": False, "financialEvents": []}],
        [{"page": 1.0, "size": 100, "hasNextPage": False, "financialEvents": []}],
        [{"page": 1, "size": 100, "hasNextPage": False}],
        [{"page": 1, "size": 100, "hasNextPage": "false", "financialEvents": []}],
        [],
    ],
)
def test_incomplete_or_invalid_pagination_preserves_previous_snapshot(db, invalid):
    tenant = store(db)
    original = imported(db, tenant, financial_event())
    with tenant_context(tenant), pytest.raises(IfoodFinancialError):
        import_financial_pages(db, tenant, MERCHANT, BEGIN, END, invalid, actor_id=7)
    assert report(db, tenant) == original


def test_complete_multiple_pages_are_imported_together(db):
    tenant = store(db)
    with tenant_context(tenant):
        result = import_financial_pages(
            db,
            tenant,
            MERCHANT,
            BEGIN,
            END,
            pages(
                financial_event(), financial_event("ORDER_COMMISSION", "-10"), size=1
            ),
            actor_id=7,
        )
        db.commit()
    assert result["metadata"]["page_count"] == 2
    assert result["summary"]["event_count"] == 2


def test_persistence_failure_restores_previous_active_snapshot(db, monkeypatch):
    tenant = store(db)
    original = imported(db, tenant, financial_event())
    original_flush = db.flush

    def failing_flush(*args, **kwargs):
        if any(isinstance(row, IfoodFinancialEvent) for row in db.new):
            raise RuntimeError("Falha ficticia na persistencia")
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db, "flush", failing_flush)
    with pytest.raises(RuntimeError, match="Falha ficticia"):
        imported(db, tenant, financial_event(value="92"))
    monkeypatch.setattr(db, "flush", original_flush)
    assert report(db, tenant) == original
    with tenant_context(tenant):
        assert db.query(IfoodFinancialSnapshot).count() == 1


@pytest.mark.parametrize(
    "value",
    [
        "NaN",
        "Infinity",
        "-Infinity",
        "1.001",
        "9999999999999999999999",
        True,
        None,
        "1,20",
    ],
)
def test_invalid_provider_money_never_overwrites_previous_import(db, value):
    tenant = store(db)
    original = imported(db, tenant, financial_event())
    with pytest.raises(IfoodFinancialError):
        imported(db, tenant, financial_event(value=value))
    assert report(db, tenant) == original


@pytest.mark.parametrize(
    "receiver",
    [
        {"businessId": str(uuid4()), "businessType": "MERCHANT"},
        {"businessId": MERCHANT, "businessType": "OTHER"},
        {"businessId": MERCHANT},
        {"merchantId": str(uuid4())},
    ],
)
def test_receiver_must_identify_the_expected_merchant(db, receiver):
    tenant = store(db)
    with pytest.raises(IfoodFinancialError):
        imported(db, tenant, financial_event(receiver=receiver))
    assert report(db, tenant)["imported"] is False


def test_legacy_merchant_receiver_is_supported_but_document_and_unknown_fields_are_dropped(
    db,
):
    tenant = store(db)
    event = financial_event(
        receiver={"merchantId": MERCHANT, "merchantDocument": "secret-document"},
        customer={"name": "Private Person"},
        description="Contact private@example.test",
    )
    imported(db, tenant, event)
    with tenant_context(tenant):
        evidence = db.query(IfoodFinancialEvent).one().evidence
        assert evidence["receiver"] == {"merchantId": MERCHANT}
        assert evidence["description"] is None
        assert "secret-document" not in str(evidence)
        assert "Private Person" not in str(evidence)
        assert "private@example.test" not in str(evidence)


def test_current_receiver_evidence_does_not_keep_business_document(db):
    tenant = store(db)
    imported(db, tenant, financial_event())
    with tenant_context(tenant):
        evidence = db.query(IfoodFinancialEvent).one().evidence
        assert evidence["receiver"] == {
            "businessType": "MERCHANT",
            "businessId": MERCHANT,
        }
        assert "businessDocument" not in str(evidence)


def test_costs_are_versioned_and_unknown_is_different_from_explicit_zero(db):
    tenant = store(db)
    imported(
        db,
        tenant,
        financial_event(value="0"),
        financial_event("ORDER_COMMISSION", "0"),
        financial_event("PAYMENT_TRANSACTION_FEE", "0"),
    )
    unknown = costs(db, tenant, cmv=None)
    assert unknown["contribution"]["calculated"] is False
    assert "CMV da venda" in unknown["contribution"]["missing"]
    zero = costs(db, tenant, revenue="0", cmv="0", tax="0", other_costs="0")
    assert zero["contribution"]["calculated"] is True
    assert zero["contribution"]["amount"] == "0.00"
    assert zero["contribution"]["percent"] is None
    assert zero["manual_costs"]["version"] == 2
    with tenant_context(tenant):
        versions = (
            db.query(IfoodFinancialOrderCosts)
            .order_by(IfoodFinancialOrderCosts.version)
            .all()
        )
        assert versions[0].cmv is None and versions[1].cmv == Decimal("0")
        assert versions[0].actor_id == versions[1].actor_id == 9


@pytest.mark.parametrize("value", ["-1", "NaN", "1.001", True])
def test_invalid_manual_costs_are_not_recorded(db, value):
    tenant = store(db)
    imported(db, tenant, financial_event())
    with pytest.raises(IfoodFinancialError):
        costs(db, tenant, cmv=value)
    assert report(db, tenant)["orders"][0]["manual_costs"] is None


@pytest.mark.parametrize(
    "event",
    [
        financial_event("UNKNOWN_FEE", "-3"),
        financial_event("ORDER_COMMISSION", "11.52", trigger="SALE_CANCELLED"),
        financial_event("ORDER_PAYMENT", "91", trigger="NO_CONCLUDED_STATUS"),
    ],
)
def test_unknown_or_adjustment_events_are_visible_but_block_contribution(db, event):
    tenant = store(db)
    imported(db, tenant, event)
    result = costs(db, tenant)
    assert result["contribution"]["calculated"] is False
    assert result["pending"]
    assert report(db, tenant)["orders"][0]["events"][0]["amount"] == format(
        Decimal(event["amount"]["value"]), ".2f"
    )


def test_unallocated_events_block_contribution_without_inventing_rateio(db):
    tenant = store(db)
    unallocated = financial_event(
        "MONTHLY_FEE",
        "-100",
        reference={"type": "BILLING", "id": "monthly-billing", "date": None},
        trigger="MONTHLY_FEE",
    )
    imported(db, tenant, financial_event(), unallocated)
    saved = costs(db, tenant)
    assert saved["contribution"]["calculated"] is False
    result = report(db, tenant)
    assert result["summary"]["unallocated_events"] == 1
    assert result["summary"]["transfer_impact"] == "-9.00"
    assert result["orders"][0]["totals"]["fees"] == "0.00"


def test_empty_complete_window_is_evidence_but_absent_window_has_unknown_totals(db):
    tenant = store(db)
    assert report(db, tenant)["summary"]["fees"] is None
    empty = imported(db, tenant)
    assert empty["imported"] is True and empty["metadata"]["completeness"] == "complete"
    assert empty["summary"]["fees"] == "0.00" and empty["orders"] == []


def test_same_order_in_disjoint_windows_remains_pending_instead_of_claiming_full_cost(
    db,
):
    tenant = store(db)
    imported(db, tenant, financial_event())
    imported(
        db,
        tenant,
        financial_event(
            "ORDER_COMMISSION",
            "-10",
            period={"beginDate": "2025-03-03", "endDate": "2025-03-04"},
        ),
        begin="2025-03-03",
        end="2025-03-04",
    )
    saved = costs(db, tenant)
    queried = report(db, tenant)["orders"][0]
    for result in (saved, queried):
        assert result["contribution"]["calculated"] is False
        assert (
            "Pedido possui lançamentos em outros períodos; conciliação necessária."
            in result["contribution"]["missing"]
        )


@pytest.mark.parametrize(
    "begin,end", [("2025-03-03", BEGIN), (BEGIN, "2025-04-03"), ("bad", END)]
)
def test_invalid_or_over_33_day_window_is_rejected(db, begin, end):
    tenant = store(db)
    with pytest.raises(IfoodFinancialError):
        report(db, tenant, begin=begin, end=end)


def test_financial_service_does_not_enable_production_mode(db):
    tenant = store(db)
    with tenant_context(tenant), pytest.raises(IfoodFinancialError):
        get_financial_report(db, tenant, MERCHANT, BEGIN, END, mode="production")


@pytest.mark.parametrize("reference", [None, {}, {"type": "BILLING", "id": None}])
def test_legitimate_events_without_order_reference_are_preserved_unallocated(
    db, reference
):
    tenant = store(db)
    result = imported(
        db,
        tenant,
        financial_event(
            "MONTHLY_FEE", "-15", reference=reference, trigger="MONTHLY_FEE"
        ),
    )
    assert result["summary"]["unallocated_events"] == 1
    assert result["summary"]["transfer_impact"] == "-15.00"
    assert result["orders"] == []
    assert result["unallocated_events"][0]["amount"] == "-15.00"
    with tenant_context(tenant):
        assert db.query(IfoodFinancialEvent).one().order_id is None


@pytest.mark.parametrize(
    "missing_name", ["ORDER_COMMISSION", "PAYMENT_TRANSACTION_FEE"]
)
def test_missing_provider_fee_blocks_contribution_even_when_manual_costs_are_complete(
    db, missing_name
):
    tenant = store(db)
    imported(
        db,
        tenant,
        financial_event(),
        *(
            financial_event(name, "0")
            for name in ("ORDER_COMMISSION", "PAYMENT_TRANSACTION_FEE")
            if name != missing_name
        ),
    )
    result = costs(db, tenant)
    assert result["contribution"]["calculated"] is False
    assert any(
        "ainda não informada pelo iFood" in message
        for message in result["contribution"]["missing"]
    )
    assert result["manual_costs"]["cmv"] == "60.00"


def _migration():
    return runpy.run_path(
        str(
            Path(__file__).resolve().parents[2]
            / "alembic"
            / "versions"
            / "zzzzo20261023a1_ifood_financial_snapshots.py"
        )
    )


def test_financial_migration_creates_numeric_amounts_tenant_keys_and_reversible_tables():
    engine = create_engine("sqlite:///:memory:")
    migration = _migration()
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration["upgrade"]()
            inspector = inspect(connection)
            assert set(inspector.get_table_names()) == set(migration["TABLE_NAMES"])
            columns = {
                column["name"]: column
                for column in inspector.get_columns("ifood_financial_events")
            }
            assert columns["tenant_id"]["nullable"] is False
            assert columns["amount"]["type"].precision == 18
            assert columns["amount"]["type"].scale == 2
            foreign_key = inspector.get_foreign_keys("ifood_financial_events")[0]
            assert foreign_key["constrained_columns"] == ["tenant_id", "snapshot_id"]
            assert foreign_key["referred_columns"] == ["tenant_id", "id"]
            costs_columns = {
                column["name"]: column
                for column in inspector.get_columns("ifood_financial_order_costs")
            }
            assert all(
                costs_columns[field]["nullable"]
                for field in ("revenue", "cmv", "tax", "other_costs")
            )
            migration["downgrade"]()
            assert inspect(connection).get_table_names() == []
    engine.dispose()


def test_financial_migration_enables_and_forces_tenant_rls_on_all_new_tables(
    monkeypatch,
):
    migration = _migration()
    op, sa = migration["op"], migration["sa"]
    emitted = []
    bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    monkeypatch.setattr(op, "get_bind", lambda: bind)
    monkeypatch.setattr(op, "create_table", lambda *args, **kwargs: None)
    monkeypatch.setattr(op, "create_index", lambda *args, **kwargs: None)
    monkeypatch.setattr(op, "execute", lambda statement: emitted.append(str(statement)))
    monkeypatch.setattr(
        sa, "inspect", lambda _bind: SimpleNamespace(has_table=lambda _table: True)
    )
    migration["upgrade"]()
    for table in migration["TABLE_NAMES"]:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in emitted
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in emitted
        policy = next(
            statement
            for statement in emitted
            if statement.startswith(f"CREATE POLICY {table}_tenant_isolation")
        )
        assert (
            "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
            in policy
        )
        assert (
            "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
            in policy
        )
