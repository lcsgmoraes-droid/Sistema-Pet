from decimal import Decimal
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import (  # noqa: F401 - register ORM relationships
    caixa_models,
    dre_plano_contas_models,
    ecommerceai_integration_models,
    financeiro_models,
    models,
    ofertas_estudio_models,
    produtos_models,
    vendas_models,
)
from app.campaigns.models import (
    CampaignTypeEnum,
    CashbackSourceTypeEnum,
    CouponStatusEnum,
)
from app.campaigns.clientes_routes import relatorio_campanhas
from app.campaigns.beneficios_manuais_routes import estornar_carimbo
from app.campaigns.loyalty_service import sync_loyalty_stamps_for_sale
from app.campaigns.handlers.quick_repurchase import QuickRepurchaseHandler
from app.campaigns.sale_return_service import (
    _cashback_reversal_amount,
    _reconcile_loyalty,
    _reconcile_quick_repurchase,
    prepare_purchase_event,
    preflight_purchase_benefits_on_return,
    reconcile_purchase_benefits_on_return,
)
from app.campaigns.scheduler_jobs import _expire_cashback_credit_if_needed
from app.campaigns.statement_service_parts.cashback import _add_cashback_events


@pytest.mark.parametrize(
    "grant,reversed_amount,expired_amount,base,retained,expected",
    [
        ("10", "0", "0", "200", "100", "5.00"),
        ("10", "5", "0", "200", "0", "5.00"),
        ("10", "5", "0", "200", "100", "0.00"),
        ("10", "0", "10", "200", "0", "0.00"),
        ("10", "0", "3", "200", "100", "5.00"),
    ],
)
def test_cashback_refund_reverses_only_unearned_unexpired_balance(
    grant, reversed_amount, expired_amount, base, retained, expected
):
    assert _cashback_reversal_amount(
        grant=Decimal(grant),
        reversed_amount=Decimal(reversed_amount),
        expired_amount=Decimal(expired_amount),
        base_sale_total=Decimal(base),
        retained_sale_total=Decimal(retained),
    ) == Decimal(expected)


class _Query:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []
        self.locked = False

    def filter(self, *args):
        return self

    def with_for_update(self):
        self.locked = True
        return self

    def first(self):
        return self.row

    def all(self):
        return self.rows


def test_pending_purchase_event_uses_retained_value_under_sale_lock(monkeypatch):
    venda = SimpleNamespace(
        id=42,
        tenant_id="tenant",
        cliente_id=8,
        status="finalizada_devolucao",
        total=Decimal("200"),
        canal="loja_fisica",
    )
    query = _Query(row=venda)
    db = SimpleNamespace(query=lambda model: query)
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.remaining_sale_amount",
        lambda db, *, tenant_id, venda: Decimal("100.00"),
    )

    payload = prepare_purchase_event(
        db,
        tenant_id="tenant",
        payload={"venda_id": 42, "customer_id": 8, "venda_total": 200},
    )

    assert query.locked is True
    assert payload["venda_total"] == 100.0
    assert payload["venda_total_original"] == 200.0


def test_return_rejects_previously_used_quick_repurchase_coupon(monkeypatch):
    coupon = SimpleNamespace(
        id=7,
        campaign_id=9,
        customer_id=8,
        code="VOLTE",
        status=CouponStatusEnum.used,
        meta={
            "source_kind": "quick_repurchase",
            "source_venda_id": 42,
            "min_purchase_value_snapshot": "150",
        },
    )
    campaign = SimpleNamespace(id=9, params={"min_purchase_value": 50})
    coupon_query = _Query(rows=[coupon])
    campaign_query = _Query(row=campaign)
    db = SimpleNamespace(
        query=lambda model: (
            coupon_query if model.__name__ == "Coupon" else campaign_query
        )
    )

    with pytest.raises(HTTPException) as exc:
        _reconcile_quick_repurchase(
            db,
            tenant_id="tenant",
            venda=SimpleNamespace(id=42, cliente_id=8),
            retained=Decimal("100"),
            evento_devolucao=SimpleNamespace(id=3),
        )

    assert exc.value.status_code == 409
    assert coupon_query.locked is True
    assert coupon.status == CouponStatusEnum.used


def test_return_voids_unearned_quick_repurchase_coupon(monkeypatch):
    coupon = SimpleNamespace(
        id=7,
        campaign_id=9,
        customer_id=8,
        code="VOLTE",
        status=CouponStatusEnum.active,
        meta={
            "source_kind": "quick_repurchase",
            "source_venda_id": 42,
            "min_purchase_value_snapshot": "150",
        },
    )
    campaign = SimpleNamespace(id=9, params={"min_purchase_value": 50})
    db = SimpleNamespace(
        query=lambda model: (
            _Query(rows=[coupon])
            if model.__name__ == "Coupon"
            else _Query(row=campaign)
        )
    )
    audit_events = []
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.log_campaign_event",
        lambda **kwargs: audit_events.append(kwargs),
    )

    voided = _reconcile_quick_repurchase(
        db,
        tenant_id="tenant",
        venda=SimpleNamespace(id=42, cliente_id=8),
        retained=Decimal("100"),
        evento_devolucao=SimpleNamespace(id=3),
    )

    assert voided == 1
    assert coupon.status == CouponStatusEnum.voided
    assert coupon.meta["source_devolucao_id"] == 3
    assert len(audit_events) == 1


def test_return_blocks_legacy_quick_coupon_without_provenance():
    sale_date = datetime(2026, 10, 5, 10, 0)
    coupon = SimpleNamespace(
        id=7,
        campaign_id=9,
        customer_id=8,
        code="VOLTE",
        status=CouponStatusEnum.active,
        meta={},
        created_at=sale_date + timedelta(minutes=1),
    )
    campaign = SimpleNamespace(
        id=9,
        campaign_type=CampaignTypeEnum.quick_repurchase,
        params={"min_purchase_value": 0},
    )
    db = SimpleNamespace(
        query=lambda model: (
            _Query(rows=[coupon])
            if model.__name__ == "Coupon"
            else _Query(row=campaign)
        )
    )

    with pytest.raises(HTTPException) as exc:
        _reconcile_quick_repurchase(
            db,
            tenant_id="tenant",
            venda=SimpleNamespace(id=42, cliente_id=8, data_venda=sale_date),
            retained=Decimal("100"),
            evento_devolucao=SimpleNamespace(id=3),
        )

    assert exc.value.status_code == 409
    assert "sem venda de origem" in exc.value.detail


def test_quick_coupon_keeps_issuance_threshold_when_campaign_changes():
    coupon = SimpleNamespace(
        id=7,
        campaign_id=9,
        customer_id=8,
        code="VOLTE",
        status=CouponStatusEnum.active,
        meta={
            "source_kind": "quick_repurchase",
            "source_venda_id": 42,
            "min_purchase_value_snapshot": "50.00",
        },
    )
    campaign = SimpleNamespace(id=9, params={"min_purchase_value": 150})
    db = SimpleNamespace(
        query=lambda model: (
            _Query(rows=[coupon])
            if model.__name__ == "Coupon"
            else _Query(row=campaign)
        )
    )

    assert (
        _reconcile_quick_repurchase(
            db,
            tenant_id="tenant",
            venda=SimpleNamespace(id=42, cliente_id=8),
            retained=Decimal("100"),
            evento_devolucao=SimpleNamespace(id=3),
        )
        == 0
    )
    assert coupon.status == CouponStatusEnum.active


def test_quick_coupon_without_historical_minimum_blocks_partial_return():
    coupon = SimpleNamespace(
        id=7,
        campaign_id=9,
        customer_id=8,
        code="VOLTE",
        status=CouponStatusEnum.active,
        meta={"source_kind": "quick_repurchase", "source_venda_id": 42},
    )
    db = SimpleNamespace(
        query=lambda model: (
            _Query(rows=[coupon])
            if model.__name__ == "Coupon"
            else _Query(row=SimpleNamespace(id=9, params={"min_purchase_value": 0}))
        )
    )

    with pytest.raises(HTTPException) as exc:
        _reconcile_quick_repurchase(
            db,
            tenant_id="tenant",
            venda=SimpleNamespace(id=42, cliente_id=8),
            retained=Decimal("100"),
            evento_devolucao=SimpleNamespace(id=3),
        )

    assert exc.value.status_code == 409
    assert coupon.status == CouponStatusEnum.active


def test_loyalty_reconciliation_uses_historical_stamp_step(monkeypatch):
    stamps = [
        SimpleNamespace(campaign_id=9, stamp_value_snapshot=Decimal("100")),
        SimpleNamespace(campaign_id=9, stamp_value_snapshot=Decimal("100")),
    ]
    campaign = SimpleNamespace(id=9, params={"min_purchase_value": 50})
    db = SimpleNamespace(
        query=lambda model: (
            _Query(rows=stamps)
            if model.__name__ == "LoyaltyStamp"
            else _Query(row=campaign)
        )
    )
    calls = []
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.sync_loyalty_stamps_for_sale",
        lambda db, **kwargs: calls.append(kwargs) or {"stamps_voided": 1, "revoked": 0},
    )

    result = _reconcile_loyalty(
        db,
        tenant_id="tenant",
        venda=SimpleNamespace(id=42, cliente_id=8),
        retained=Decimal("100"),
        evento_devolucao=SimpleNamespace(id=3),
    )

    assert result["stamps_voided"] == 1
    assert calls[0]["stamp_value_override"] == Decimal("100")


def test_loyalty_reconciliation_blocks_legacy_stamp_without_step(monkeypatch):
    stamps = [SimpleNamespace(campaign_id=9, stamp_value_snapshot=None)]
    db = SimpleNamespace(query=lambda model: _Query(rows=stamps))
    calls = []
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.sync_loyalty_stamps_for_sale",
        lambda db, **kwargs: calls.append(kwargs),
    )

    with pytest.raises(HTTPException) as exc:
        _reconcile_loyalty(
            db,
            tenant_id="tenant",
            venda=SimpleNamespace(id=42, cliente_id=8),
            retained=Decimal("100"),
            evento_devolucao=SimpleNamespace(id=3),
        )

    assert exc.value.status_code == 409
    assert calls == []


def test_return_preflight_rejects_legacy_loyalty_without_mutation():
    stamps = [
        SimpleNamespace(
            campaign_id=9,
            stamp_value_snapshot=None,
            voided_at=None,
        )
    ]
    db = SimpleNamespace(
        query=lambda model: _Query(rows=stamps),
        add=lambda obj: pytest.fail("Previa nao deve adicionar beneficios"),
        flush=lambda: pytest.fail("Previa nao deve alterar a transacao"),
    )

    with pytest.raises(HTTPException) as exc:
        preflight_purchase_benefits_on_return(
            db,
            tenant_id="tenant",
            venda=SimpleNamespace(id=42, cliente_id=8, total=Decimal("250")),
            valor_acumulado=Decimal("20"),
        )

    assert exc.value.status_code == 409


def test_return_preflight_accepts_historical_loyalty_step_without_mutation():
    stamps = [
        SimpleNamespace(
            campaign_id=9,
            stamp_value_snapshot=Decimal("100"),
            voided_at=None,
        )
    ]
    campaign = SimpleNamespace(id=9, params={"min_purchase_value": 50})
    coupon_query = _Query(rows=[])
    db = SimpleNamespace(
        query=lambda model: (
            _Query(rows=stamps)
            if model.__name__ == "LoyaltyStamp"
            else _Query(row=campaign)
            if model.__name__ == "Campaign"
            else coupon_query
        ),
        add=lambda obj: pytest.fail("Previa nao deve adicionar beneficios"),
        flush=lambda: pytest.fail("Previa nao deve alterar a transacao"),
    )

    retained = preflight_purchase_benefits_on_return(
        db,
        tenant_id="tenant",
        venda=SimpleNamespace(id=42, cliente_id=8, total=Decimal("250")),
        valor_acumulado=Decimal("20"),
    )

    assert retained == Decimal("230.00")
    assert coupon_query.locked is False


def test_return_post_revalidates_benefits_before_mutation(monkeypatch):
    checked = []

    def reject_preflight(db, **kwargs):
        checked.append(kwargs["valor_acumulado"])
        raise HTTPException(status_code=409, detail="Regra historica mudou")

    monkeypatch.setattr(
        "app.campaigns.sale_return_service.preflight_purchase_benefits_on_return",
        reject_preflight,
    )
    monkeypatch.setattr(
        "app.campaigns.sale_return_service._reconcile_cashback",
        lambda db, **kwargs: pytest.fail("Nenhum estorno pode preceder o preflight"),
    )
    db = SimpleNamespace(flush=lambda: pytest.fail("Nenhum flush antes do preflight"))

    with pytest.raises(HTTPException) as exc:
        reconcile_purchase_benefits_on_return(
            db,
            tenant_id="tenant",
            venda=SimpleNamespace(id=42, cliente_id=8, total=Decimal("250")),
            evento_devolucao=SimpleNamespace(id=3),
            valor_acumulado=Decimal("20"),
        )

    assert exc.value.status_code == 409
    assert checked == [Decimal("20")]


def test_loyalty_legacy_stamps_already_voided_manually_need_no_recalculation():
    stamps = [
        SimpleNamespace(
            campaign_id=9,
            stamp_value_snapshot=None,
            voided_at=datetime(2026, 10, 5, 12, 0),
        )
    ]
    db = SimpleNamespace(query=lambda model: _Query(rows=stamps))

    result = _reconcile_loyalty(
        db,
        tenant_id="tenant",
        venda=SimpleNamespace(id=42, cliente_id=8),
        retained=Decimal("100"),
        evento_devolucao=SimpleNamespace(id=3),
    )

    assert result == {"stamps_voided": 0, "rewards_revoked": 0}


def test_manual_stamp_removal_records_its_origin(monkeypatch):
    stamp = SimpleNamespace(
        id=12,
        campaign_id=9,
        customer_id=8,
        voided_at=None,
        voided_origin=None,
        notes=None,
    )
    campaign = SimpleNamespace(id=9)
    commits = []
    db = SimpleNamespace(
        query=lambda model: _Query(
            row=stamp if model.__name__ == "LoyaltyStamp" else campaign
        ),
        commit=lambda: commits.append(True),
    )
    monkeypatch.setattr(
        "app.campaigns.loyalty_service.sync_loyalty_rewards_for_customer",
        lambda db, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.campaigns.beneficios_manuais_routes.summarize_loyalty_balances_for_customer",
        lambda db, **kwargs: {
            "total_carimbos": 1,
            "total_carimbos_brutos": 1,
            "carimbos_comprometidos_total": 0,
            "carimbos_em_debito": 0,
            "carimbos_convertidos": 0,
        },
    )
    monkeypatch.setattr(
        "app.campaigns.beneficios_manuais_routes.build_loyalty_stamp_audit_metadata",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        "app.campaigns.beneficios_manuais_routes.log_campaign_event",
        lambda **kwargs: None,
    )

    estornar_carimbo(
        stamp_id=12,
        motivo="Conferencia manual",
        db=db,
        user_and_tenant=(SimpleNamespace(id=1), "tenant"),
    )

    assert stamp.voided_at is not None
    assert stamp.voided_origin == "manual"
    assert commits == [True]


@pytest.mark.parametrize(
    "voided_origin, expected_active, expected_awarded",
    [("manual", 1, 0), (None, 1, 0), ("automatic", 2, 1)],
)
def test_return_does_not_reactivate_manually_voided_loyalty_stamp(
    monkeypatch, voided_origin, expected_active, expected_awarded
):
    class _StampQuery(_Query):
        def order_by(self, *args):
            return self

    stamps = [
        SimpleNamespace(
            id=11,
            campaign_id=9,
            stamp_index=1,
            stamp_value_snapshot=Decimal("100"),
            voided_at=None,
            voided_origin=None,
            notes=None,
        ),
        SimpleNamespace(
            id=12,
            campaign_id=9,
            stamp_index=2,
            stamp_value_snapshot=Decimal("100"),
            voided_at=datetime(2026, 10, 5, 12, 0),
            voided_origin=voided_origin,
            notes="Estornado manualmente",
        ),
    ]
    campaign = SimpleNamespace(
        id=9,
        tenant_id="tenant",
        name="Fidelidade",
        params={"min_purchase_value": 50, "stamps_to_complete": 2},
    )
    db = SimpleNamespace(
        query=lambda model: (
            _StampQuery(rows=stamps)
            if model.__name__ == "LoyaltyStamp"
            else _Query(row=campaign)
        ),
        add=lambda obj: pytest.fail("Devolucao nao deve criar novo carimbo"),
        flush=lambda: None,
    )
    active_counts = []

    def fake_reward_sync(db, **kwargs):
        active = sum(stamp.voided_at is None for stamp in stamps)
        active_counts.append(active)
        return {
            "awarded": int(active >= 2),
            "revoked": 0,
            "total_stamps": active,
            "available_stamps": active,
            "converted_stamps": 0,
            "debt_stamps": 0,
        }

    monkeypatch.setattr(
        "app.campaigns.loyalty_service.sync_loyalty_rewards_for_customer",
        fake_reward_sync,
    )
    monkeypatch.setattr(
        "app.campaigns.loyalty_service.log_campaign_event", lambda **kwargs: None
    )

    _reconcile_loyalty(
        db,
        tenant_id="tenant",
        venda=SimpleNamespace(id=42, cliente_id=8),
        retained=Decimal("230"),
        evento_devolucao=SimpleNamespace(id=3),
    )

    assert active_counts == [expected_active]
    assert int(stamps[1].voided_at is None) == expected_awarded
    assert stamps[1].voided_origin == (
        None if voided_origin == "automatic" else voided_origin
    )


def test_new_loyalty_stamps_keep_step_used_at_award(monkeypatch):
    class _StampQuery(_Query):
        def order_by(self, *args):
            return self

    added = []
    db = SimpleNamespace(
        query=lambda model: _StampQuery(rows=[]),
        add=added.append,
        flush=lambda: None,
    )
    campaign = SimpleNamespace(
        id=9,
        tenant_id="tenant",
        name="Fidelidade",
        params={"min_purchase_value": 100},
    )
    monkeypatch.setattr(
        "app.campaigns.loyalty_service.sync_loyalty_rewards_for_customer",
        lambda db, **kwargs: {
            "awarded": 0,
            "revoked": 0,
            "total_stamps": 2,
            "available_stamps": 2,
            "converted_stamps": 0,
            "debt_stamps": 0,
        },
    )
    monkeypatch.setattr(
        "app.campaigns.loyalty_service.log_campaign_event",
        lambda **kwargs: None,
    )

    result = sync_loyalty_stamps_for_sale(
        db,
        campaign=campaign,
        customer_id=8,
        venda_id=42,
        venda_total=Decimal("250"),
    )

    assert result["stamps_added"] == 2
    assert [stamp.stamp_value_snapshot for stamp in added] == [
        Decimal("100"),
        Decimal("100"),
    ]


def test_reprocessed_loyalty_sale_uses_its_original_step(monkeypatch):
    class _StampQuery(_Query):
        def order_by(self, *args):
            return self

    original_stamp = SimpleNamespace(
        id=11,
        stamp_index=1,
        stamp_value_snapshot=Decimal("100"),
        voided_at=None,
        notes=None,
    )
    added = []
    db = SimpleNamespace(
        query=lambda model: _StampQuery(rows=[original_stamp]),
        add=added.append,
        flush=lambda: None,
    )
    campaign = SimpleNamespace(
        id=9,
        tenant_id="tenant",
        name="Fidelidade",
        params={"min_purchase_value": 50},
    )
    monkeypatch.setattr(
        "app.campaigns.loyalty_service.sync_loyalty_rewards_for_customer",
        lambda db, **kwargs: {
            "awarded": 0,
            "revoked": 0,
            "total_stamps": 1,
            "available_stamps": 1,
            "converted_stamps": 0,
            "debt_stamps": 0,
        },
    )

    result = sync_loyalty_stamps_for_sale(
        db,
        campaign=campaign,
        customer_id=8,
        venda_id=42,
        venda_total=Decimal("100"),
    )

    assert result["expected_stamps"] == 1
    assert result["stamps_added"] == 0
    assert added == []


def test_quick_repurchase_coupon_keeps_minimum_used_at_issue(monkeypatch):
    created = []
    monkeypatch.setattr(
        "app.campaigns.handlers.quick_repurchase.create_coupon",
        lambda db, **kwargs: (
            created.append(kwargs) or SimpleNamespace(id=7, code="VOLTE")
        ),
    )
    db = SimpleNamespace(query=lambda model: _Query(row=None))
    campaign = SimpleNamespace(
        id=9,
        tenant_id="tenant",
        campaign_type=CampaignTypeEnum.quick_repurchase,
        params={"min_purchase_value": 150},
    )
    event = SimpleNamespace(
        id=5,
        event_type="purchase_completed",
        payload={"customer_id": 8, "venda_id": 42, "venda_total": 200},
    )

    result = QuickRepurchaseHandler().run(db, campaign, event)

    assert result["rewarded"] == 1
    assert created[0]["meta"]["source_venda_id"] == 42
    assert created[0]["meta"]["min_purchase_value_snapshot"] == "150"


@pytest.mark.parametrize(
    "reversed_amount,expected_expiration",
    [("5.00", Decimal("-5.00")), ("10.00", None)],
)
def test_cashback_expiration_accounts_for_prior_return_reversals(
    reversed_amount, expected_expiration
):
    grant = SimpleNamespace(id=12, customer_id=8, amount=Decimal("10.00"))
    queries = [
        _Query(row=grant),
        _Query(row=None),
        _Query(rows=[(-Decimal(reversed_amount),)]),
        _Query(row=None),
    ]
    added = []

    def query(model):
        return queries.pop(0)

    db = SimpleNamespace(query=query, add=added.append)
    _expire_cashback_credit_if_needed(db, SimpleNamespace(id="tenant"), grant)

    if expected_expiration is None:
        assert added == []
    else:
        assert len(added) == 1
        assert added[0].amount == expected_expiration


def test_cashback_reversal_statement_links_original_sale_not_grant_id():
    now = datetime(2026, 10, 5, 12, 0)
    grant = SimpleNamespace(
        id=11,
        source_type="campaign",
        source_id=21,
        amount=Decimal("10.00"),
        created_at=now,
        expires_at=None,
        tx_type="credit",
        description="Compra",
    )
    reversal = SimpleNamespace(
        id=12,
        source_type="reversal",
        source_id=11,
        amount=Decimal("-5.00"),
        created_at=now,
        expires_at=None,
        tx_type="debit",
        description="Devolucao parcial",
    )
    execution = SimpleNamespace(id=21, campaign_id=9, reward_meta={"venda_id": 42})
    campaign = SimpleNamespace(id=9, name="Cashback", campaign_type="cashback")
    db = SimpleNamespace(
        query=lambda model: (
            _Query(rows=[grant, reversal])
            if model.__name__ == "CashbackTransaction"
            else _Query(rows=[execution])
        )
    )
    events = []

    _add_cashback_events(
        db,
        events,
        tenant_id="tenant",
        customer_id=8,
        campaign_map={9: campaign},
        start_dt=None,
        end_dt=None,
    )

    reversed_event = next(event for event in events if event["tipo"] == "debit")
    assert reversed_event["venda_id"] == 42
    assert reversed_event["campanha_id"] == 9


def test_anonymous_full_return_reverses_coupon_redemption(monkeypatch):
    reversed_sales = []
    flushed = []
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.reverse_coupon_redemptions_for_sale",
        lambda db, **kwargs: reversed_sales.append(kwargs) or {"redemptions_voided": 1},
    )
    db = SimpleNamespace(flush=lambda: flushed.append(True))

    result = reconcile_purchase_benefits_on_return(
        db,
        tenant_id="tenant",
        venda=SimpleNamespace(id=42, cliente_id=None, total=Decimal("200")),
        evento_devolucao=SimpleNamespace(id=3),
        valor_acumulado=Decimal("200"),
    )

    assert reversed_sales[0]["venda_id"] == 42
    assert result["coupon_redemptions_reversed"] == 1
    assert flushed == [True]


def test_anonymous_partial_return_keeps_coupon_redemption(monkeypatch):
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.reverse_coupon_redemptions_for_sale",
        lambda db, **kwargs: (_ for _ in ()).throw(
            AssertionError("Cupom nao deve ser restaurado em devolucao parcial")
        ),
    )
    db = SimpleNamespace(flush=lambda: None)

    result = reconcile_purchase_benefits_on_return(
        db,
        tenant_id="tenant",
        venda=SimpleNamespace(id=42, cliente_id=None, total=Decimal("200")),
        evento_devolucao=SimpleNamespace(id=3),
        valor_acumulado=Decimal("100"),
    )

    assert result["coupon_redemptions_reversed"] == 0


def test_campaign_report_does_not_count_reversal_as_sale_redemption():
    now = datetime(2026, 10, 5, 12, 0)
    transactions = [
        SimpleNamespace(
            id=11,
            customer_id=8,
            amount=Decimal("10"),
            source_type=CashbackSourceTypeEnum.campaign,
            source_id=21,
            created_at=now,
            description="Credito",
        ),
        SimpleNamespace(
            id=12,
            customer_id=8,
            amount=Decimal("-5"),
            source_type=CashbackSourceTypeEnum.reversal,
            source_id=11,
            created_at=now,
            description="Estorno devolucao",
        ),
        SimpleNamespace(
            id=13,
            customer_id=8,
            amount=Decimal("-2"),
            source_type=CashbackSourceTypeEnum.redemption,
            source_id=42,
            created_at=now,
            description="Resgate",
        ),
    ]

    class _ReportQuery(_Query):
        def order_by(self, *args):
            return self

        def limit(self, count):
            return self

    db = SimpleNamespace(
        query=lambda model: (
            _ReportQuery(rows=transactions)
            if model.__name__ == "CashbackTransaction"
            else _ReportQuery(rows=[SimpleNamespace(id=8, nome="Cliente")])
            if model.__name__ == "Cliente"
            else _ReportQuery(rows=[SimpleNamespace(id=42, numero_venda="V-42")])
        )
    )

    report = relatorio_campanhas(
        data_inicio=None,
        data_fim=None,
        tipo=None,
        db=db,
        user_and_tenant=(None, "tenant"),
    )

    reversal = next(row for row in report["transacoes"] if row["id"] == 12)
    assert reversal["tipo"] == "estorno"
    assert reversal["venda_id"] is None
    assert report["total_resgatado"] == 2.0
    assert report["saldo_total"] == 3.0
