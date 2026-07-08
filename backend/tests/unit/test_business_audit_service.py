from types import SimpleNamespace
from uuid import UUID

import pytest

from app.middlewares.request_context import clear_request_context, set_request_id
from app.services import business_audit_service


def test_log_business_event_records_request_id_and_redacts_sensitive_metadata(
    monkeypatch,
):
    captured = {}
    structured_logs = []

    def fake_log_action(**kwargs):
        captured.update(kwargs)
        return "audit-row"

    monkeypatch.setattr(business_audit_service, "log_action", fake_log_action)
    monkeypatch.setattr(
        business_audit_service.structured_logger,
        "info",
        lambda event, message, **kwargs: structured_logs.append(
            {"event": event, "message": message, **kwargs}
        ),
    )
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
    assert structured_logs == [
        {
            "event": "business_event",
            "message": "Business audit event recorded",
            "business_event": "sale.manual_discount_finalized",
            "request_id": "req-sale-123",
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "user_id": 7,
            "entity_type": "vendas",
            "entity_id": 55,
            "action": "business.sale.manual_discount_finalized",
            "metadata": {
                "discount_amount": 25.0,
                "token": "***REDACTED***",
                "nested": {"senha": "***REDACTED***", "reason": "cliente fiel"},
            },
            "commit": False,
        }
    ]


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

    assert business_audit_service.calculate_manual_discount_amount(
        venda
    ) == pytest.approx(25.0)


def test_calculate_manual_discount_amount_returns_zero_when_discount_is_coupon_only():
    venda = SimpleNamespace(desconto_valor=20, cupom_discount_applied=20)

    assert business_audit_service.calculate_manual_discount_amount(
        venda
    ) == pytest.approx(0.0)


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


def test_build_user_access_metadata_normalizes_actor_target_and_role():
    actor = SimpleNamespace(id=1, email="admin@example.com")
    target = SimpleNamespace(id=2, email="operador@example.com")
    role = SimpleNamespace(id=3, name="Operador")

    metadata = business_audit_service.build_user_access_metadata(
        actor=actor,
        target_user=target,
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        role=role,
        extra={"is_active": True},
    )

    assert metadata == {
        "actor_user_id": 1,
        "actor_email": "admin@example.com",
        "target_user_id": 2,
        "target_email": "operador@example.com",
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "role_id": 3,
        "role_name": "Operador",
        "is_active": True,
    }


def test_build_module_activation_metadata_records_before_after_state():
    tenant = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"), plan="basico"
    )

    metadata = business_audit_service.build_module_activation_metadata(
        tenant=tenant,
        module="campanhas",
        previous_modules=["entregas"],
        current_modules=["campanhas", "entregas"],
        subscription_created=True,
    )

    assert metadata == {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "tenant_plan": "basico",
        "module": "campanhas",
        "previous_modules": ["entregas"],
        "current_modules": ["campanhas", "entregas"],
        "subscription_created": True,
    }


def test_build_plan_activation_metadata_records_previous_and_current_state():
    activated_at = "2026-05-16T22:00:00+00:00"
    tenant = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        plan="basico",
        billing_status="active",
        subscription_source="manual",
        subscription_activated_at=SimpleNamespace(isoformat=lambda: activated_at),
        trial_started_at=None,
        trial_ends_at=None,
    )
    previous_state = {"plan": "trial", "billing_status": "trial"}

    metadata = business_audit_service.build_plan_activation_metadata(
        tenant=tenant,
        previous_state=previous_state,
    )

    assert metadata == {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "previous": previous_state,
        "current": {
            "plan": "basico",
            "billing_status": "active",
            "subscription_source": "manual",
            "subscription_activated_at": activated_at,
            "trial_started_at": None,
            "trial_ends_at": None,
        },
    }


def test_build_bank_cutover_metadata_records_safe_summary_only():
    metadata = business_audit_service.build_bank_cutover_metadata(
        payload=SimpleNamespace(
            data_corte="2026-07-08",
            conta_bancaria_id=12,
            saldo_real=1500.25,
            expected_saldo_atual=-120.5,
            baixar_historico=True,
            ajustar_saldo=True,
        ),
        resultado={
            "resumo": {
                "contas_receber_baixadas": 4,
                "valor_receber_baixado": "1000.00",
                "contas_pagar_baixadas": 2,
                "valor_pagar_baixado": "350.00",
                "saldo_bancario_alterado": True,
            },
            "saldo_bancario": {
                "conta_bancaria_id": 12,
                "nome": "Santander",
                "saldo_atual_antes": "-120.50",
                "saldo_atual_depois": "1500.25",
                "diferenca": "1620.75",
            },
            "contas_receber": [{"id": 1}, {"id": 2}],
            "contas_pagar": [{"id": 3}],
        },
    )

    assert metadata == {
        "data_corte": "2026-07-08",
        "conta_bancaria_id": 12,
        "saldo_real": "1500.25",
        "expected_saldo_atual": "-120.50",
        "baixar_historico": True,
        "ajustar_saldo": True,
        "resumo": {
            "contas_receber_baixadas": 4,
            "valor_receber_baixado": "1000.00",
            "contas_pagar_baixadas": 2,
            "valor_pagar_baixado": "350.00",
            "saldo_bancario_alterado": True,
        },
        "saldo_bancario": {
            "conta_bancaria_id": 12,
            "nome": "Santander",
            "saldo_atual_antes": "-120.50",
            "saldo_atual_depois": "1500.25",
            "diferenca": "1620.75",
        },
    }
    assert "contas_receber" not in metadata
    assert "contas_pagar" not in metadata
