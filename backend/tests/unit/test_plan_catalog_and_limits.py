from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.routes.modulos_routes import _resolver_modulos_ativos
from app.security.module_access import _load_active_entitlements
from app.services.plan_catalog import (
    ALL_PUBLIC_ENTITLEMENTS,
    PLAN_CATALOG,
    get_plan,
    resolve_signup_selection,
)
from app.services.plan_limits import (
    enforce_monthly_sales_limit,
    enforce_simultaneous_session_limit,
)


def _tenant(plan: str, **overrides):
    values = {
        "id": "tenant-1",
        "plan": plan,
        "billing_status": "active",
        "trial_started_at": None,
        "trial_ends_at": None,
        "subscription_source": "manual",
        "subscription_activated_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_catalog_matches_the_public_plan_ladder():
    assert get_plan("basico").code == "pet-basico"
    assert PLAN_CATALOG["pet-start"].price_cents == 4_990
    assert PLAN_CATALOG["pet-start"].monthly_sales_limit == 300
    assert PLAN_CATALOG["pet-start"].simultaneous_sessions_limit == 1
    assert PLAN_CATALOG["pet-basico"].monthly_sales_limit is None
    assert PLAN_CATALOG["grooming-completo"].price_cents == 15_700


def test_signup_plan_defines_and_validates_the_business_profile():
    plan, organization = resolve_signup_selection("vet-start", "hospital")
    assert plan.code == "vet-start"
    assert organization == "hospital"

    with pytest.raises(ValueError, match="nao pertence"):
        resolve_signup_selection("grooming-start", "petshop")


def test_plan_modules_are_active_after_trial_without_manual_activation():
    active = _resolver_modulos_ativos(
        raw_modulos=None,
        assinaturas_ativas=[],
        agora=datetime(2026, 7, 18, tzinfo=timezone.utc),
        plano="pet-gestao",
    )

    assert "compras" in active
    assert "financeiro_erp" in active
    assert "ecommerce" not in active


def test_pet_basico_has_xml_but_not_purchase_suggestions():
    tenant = _tenant("pet-basico")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = tenant

    active = _load_active_entitlements(
        db, tenant.id, datetime(2026, 7, 18, tzinfo=timezone.utc)
    )

    assert "purchases.invoice_xml" in active
    assert "purchases.suggestions" not in active


def test_active_trial_temporarily_releases_every_public_entitlement():
    now = datetime(2026, 7, 18, tzinfo=timezone.utc)
    tenant = _tenant(
        "pet-start",
        billing_status="trial",
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=30),
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = tenant

    active = _load_active_entitlements(db, tenant.id, now)

    assert set(active) == set(ALL_PUBLIC_ENTITLEMENTS)


def test_pet_start_blocks_the_301st_non_cancelled_sale():
    tenant_query = MagicMock()
    tenant_query.filter.return_value.with_for_update.return_value.first.return_value = (
        _tenant("pet-start")
    )
    sales_query = MagicMock()
    sales_query.filter.return_value.count.return_value = 300
    db = MagicMock()
    db.query.side_effect = [tenant_query, sales_query]

    with pytest.raises(HTTPException) as exc:
        enforce_monthly_sales_limit(db, "tenant-1", datetime(2026, 7, 18, 12, 0))

    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "monthly_sales_limit_reached"
    assert exc.value.detail["uso"] == 300


def test_trial_does_not_apply_the_selected_plan_limit():
    now = datetime(2026, 7, 18, tzinfo=timezone.utc)
    tenant_query = MagicMock()
    tenant_query.filter.return_value.with_for_update.return_value.first.return_value = (
        _tenant(
            "pet-start",
            billing_status="trial",
            trial_started_at=now,
            trial_ends_at=now + timedelta(days=30),
        )
    )
    db = MagicMock()
    db.query.return_value = tenant_query

    enforce_monthly_sales_limit(db, "tenant-1")

    assert db.query.call_count == 1


def test_expired_trial_blocks_new_sales_until_activation():
    now = datetime(2026, 7, 18, tzinfo=timezone.utc)
    tenant_query = MagicMock()
    tenant_query.filter.return_value.with_for_update.return_value.first.return_value = (
        _tenant(
            "pet-start",
            billing_status="trial",
            trial_started_at=now - timedelta(days=31),
            trial_ends_at=now - timedelta(days=1),
        )
    )
    db = MagicMock()
    db.query.return_value = tenant_query

    with pytest.raises(HTTPException) as exc:
        enforce_monthly_sales_limit(db, "tenant-1")

    assert exc.value.status_code == 402
    assert exc.value.detail["code"] == "subscription_inactive"


def test_new_start_login_revokes_previous_tenant_sessions():
    now = datetime(2026, 7, 18, tzinfo=timezone.utc)
    old_sessions = [
        SimpleNamespace(token_jti="old-1", revoked=False),
        SimpleNamespace(token_jti="old-2", revoked=False),
    ]
    query = MagicMock()
    query.filter.return_value.order_by.return_value.all.return_value = old_sessions
    db = MagicMock()
    db.query.return_value = query

    revoked = enforce_simultaneous_session_limit(
        db=db,
        tenant=_tenant("pet-start"),
        current_session=SimpleNamespace(token_jti="new"),
        now_utc=now,
    )

    assert revoked == 2
    assert all(session.revoked for session in old_sessions)
    assert all(
        session.revoke_reason == "plan_simultaneous_session_limit"
        for session in old_sessions
    )
