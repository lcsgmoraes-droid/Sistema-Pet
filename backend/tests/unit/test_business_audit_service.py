from types import SimpleNamespace
from uuid import UUID

import pytest

from app.middlewares.request_context import clear_request_context, set_request_id
from app.services import business_audit_service


def test_log_business_event_records_request_id_and_redacts_sensitive_metadata(monkeypatch):
    captured = {}

    def fake_log_action(**kwargs):
        captured.update(kwargs)
        return "audit-row"

    monkeypatch.setattr(business_audit_service, "log_action", fake_log_action)
    set_request_id("req-sale-123")

    try:
        result = business_audit_service.log_business_event(
            db=object(),
            tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
            user_id=7,
            event="sale.manual_discount_finalized",
            entity_type="vendas",
            entity_id=55,
            metadata={
                "discount_amount": 25.0,
                "token": "secret-token",
                "nested": {"senha": "123456", "reason": "cliente fiel"},
            },
        )
    finally:
        clear_request_context()

    assert result == "audit-row"
    assert captured["action"] == "business.sale.manual_discount_finalized"
    assert captured["entity_type"] == "vendas"
    assert captured["entity_id"] == 55
    assert captured["tenant_id"] == UUID("11111111-1111-1111-1111-111111111111")
    assert captured["user_id"] == 7
    assert captured["commit"] is False
    assert captured["new_value"]["event"] == "sale.manual_discount_finalized"
    assert captured["new_value"]["request_id"] == "req-sale-123"
    assert captured["new_value"]["metadata"]["discount_amount"] == pytest.approx(25.0)
    assert captured["new_value"]["metadata"]["token"] == "***REDACTED***"
    assert captured["new_value"]["metadata"]["nested"]["senha"] == "***REDACTED***"
    assert captured["new_value"]["metadata"]["nested"]["reason"] == "cliente fiel"


def test_log_business_event_truncates_action_name(monkeypatch):
    captured = {}

    def fake_log_action(**kwargs):
        captured.update(kwargs)
        return "audit-row"

    monkeypatch.setattr(business_audit_service, "log_action", fake_log_action)

    business_audit_service.log_business_event(
        db=object(),
        tenant_id="11111111-1111-1111-1111-111111111111",
        user_id=None,
        event="x" * 140,
        entity_type="vendas",
        entity_id=1,
    )

    assert len(captured["action"]) == 100
    assert captured["action"].startswith("business.")


def test_calculate_manual_discount_amount_ignores_coupon_discount():
    venda = SimpleNamespace(desconto_valor=40, cupom_discount_applied=15)

    assert business_audit_service.calculate_manual_discount_amount(venda) == pytest.approx(25.0)


def test_calculate_manual_discount_amount_returns_zero_when_discount_is_coupon_only():
    venda = SimpleNamespace(desconto_valor=20, cupom_discount_applied=20)

    assert business_audit_service.calculate_manual_discount_amount(venda) == pytest.approx(0.0)


def test_build_sale_reopened_metadata_keeps_reversal_results():
    venda = SimpleNamespace(
        numero_venda="202605160025",
        status="aberta",
        total=125.5,
        cupom_code="PROMO10",
        cliente_id=99,
    )

    metadata = business_audit_service.build_sale_reopened_metadata(
        venda=venda,
        previous_status="finalizada",
        commissions_removed=2,
        coupon_reversal={"redemptions_reversed": 1},
        loyalty_void={"stamps_voided": 10},
    )

    assert metadata["sale_number"] == "202605160025"
    assert metadata["previous_status"] == "finalizada"
    assert metadata["new_status"] == "aberta"
    assert metadata["commissions_removed"] == 2
    assert metadata["coupon_code"] == "PROMO10"
    assert metadata["customer_id"] == 99
    assert metadata["sale_total"] == pytest.approx(125.5)
    assert metadata["coupon_reversal"] == {"redemptions_reversed": 1}
    assert metadata["loyalty_void"] == {"stamps_voided": 10}


def test_build_sale_coupon_redeemed_metadata_records_core_identifiers():
    venda = SimpleNamespace(
        numero_venda="202605160025",
        total=90,
        cliente_id=99,
    )

    metadata = business_audit_service.build_sale_coupon_redeemed_metadata(
        venda=venda,
        coupon_consumed={
            "coupon_id": 8,
            "code": "PROMO10",
            "redemption_id": 123,
            "discount_applied": 10,
        },
    )

    assert metadata["sale_number"] == "202605160025"
    assert metadata["coupon_id"] == 8
    assert metadata["coupon_code"] == "PROMO10"
    assert metadata["redemption_id"] == 123
    assert metadata["discount_applied"] == pytest.approx(10.0)
    assert metadata["customer_id"] == 99
    assert metadata["sale_total"] == pytest.approx(90.0)
