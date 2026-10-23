import importlib.util
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.core import create_access_token
from app.db import Base, get_session
from app.db import base as _base  # noqa: F401 - registra os modelos relacionados.
from app.models import AssinaturaModulo, AuditLog, Tenant, User
from app.platform_auth_models import PlatformAdmin, PlatformAdminSession
from app.routes import modulos_routes, ops_tenants_routes
from app.security.module_access import _load_active_entitlements, _load_active_modules
from app.services import manual_full_access_service, plan_limits
from app.services.billing_access import manual_full_access_allowed
from app.services.manual_full_access_service import (
    ManualFullAccessError,
    grant_manual_full_access,
)
from app.services.plan_catalog import ALL_PUBLIC_ENTITLEMENTS
from app.tenancy.context import (
    clear_current_tenant,
    get_current_tenant,
    set_current_tenant,
    tenant_context,
)


NOW = datetime(2026, 10, 23, 18, tzinfo=timezone.utc)
FINANCIAL_FIELDS = (
    "plan",
    "plan_pet",
    "plan_vet",
    "plan_grooming",
    "billing_status",
    "trial_started_at",
    "trial_ends_at",
    "subscription_activated_at",
    "subscription_source",
    "billing_provider_subscription_id",
    "billing_provider_payment_id",
    "billing_payment_status",
    "billing_type",
    "billing_next_due_date",
    "billing_checkout_url",
)


@pytest.fixture()
def setup():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Tenant.__table__,
            AssinaturaModulo.__table__,
            AuditLog.__table__,
            PlatformAdmin.__table__,
            PlatformAdminSession.__table__,
        ],
    )
    db = Session(engine, expire_on_commit=False)
    tenants = [
        Tenant(
            id=str(uuid4()),
            name=f"Loja {i}",
            name_normalized=f"loja {i}",
            status="active",
            plan="pet-start",
            plan_pet="pet-start",
            billing_status="trial",
            trial_started_at=NOW - timedelta(days=31),
            trial_ends_at=NOW - timedelta(days=1),
            subscription_activated_at=NOW - timedelta(days=2),
            subscription_source="asaas",
            billing_provider_subscription_id="sub-teste",
            billing_provider_payment_id="pay-teste",
            billing_payment_status="OVERDUE",
            billing_next_due_date=date(2026, 10, 22),
            billing_type="PIX",
            billing_checkout_url="https://www.asaas.com/teste",
        )
        for i in range(2)
    ]
    admin = PlatformAdmin(
        id=41,
        email="plataforma@example.test",
        name="Operador",
        hashed_password="nao-usado-no-teste",
        is_active=True,
    )
    db.add_all([*tenants, admin])
    db.commit()
    try:
        yield db, tenants, admin
    finally:
        db.close()
        clear_current_tenant()
        engine.dispose()


def grant(db, tenant, admin, **kwargs):
    return grant_manual_full_access(
        db,
        tenant=tenant,
        actor_platform_admin_id=admin.id,
        motivo="FULL permanente autorizado pelo responsavel da plataforma.",
        **kwargs,
    )


class ReadQuery:
    def __init__(self, model, tenants):
        self.model = model
        self.tenants = tenants

    def filter(self, *criteria):
        self.tenant_id = str(criteria[0].right.value)
        return self

    def first(self):
        return self.tenants.get(self.tenant_id)

    def all(self):
        return []


class ReadDb:
    def __init__(self, tenants):
        self.tenants = {tenant.id: tenant for tenant in tenants}

    def query(self, model):
        return ReadQuery(model, self.tenants)


def test_grant_preserves_financial_facts_and_audits_real_platform_admin(setup):
    db, (other, target), admin = setup
    before = {field: getattr(target, field) for field in FINANCIAL_FIELDS}
    set_current_tenant(UUID(other.id))
    result = grant(db, target, admin)
    assert result["acesso_completo_manual"] is True
    assert get_current_tenant() == UUID(other.id)
    assert target.manual_full_access is True
    assert other.manual_full_access is False
    assert {field: getattr(target, field) for field in FINANCIAL_FIELDS} == before
    with tenant_context(target.id):
        audit = db.query(AuditLog).one()
        assert audit.user_id is None
        assert json.loads(audit.old_value) == {"manual_full_access": False}
        payload = json.loads(audit.new_value)
        assert payload["event"] == "config.manual_full_access_granted"
        assert payload["metadata"]["actor_platform_admin_id"] == admin.id
        assert "FULL permanente" in payload["metadata"]["reason"]
        assert payload["metadata"]["manual_full_access"] is True
    with tenant_context(other.id):
        assert db.query(AuditLog).count() == 0


def test_manual_grant_is_permanent_full_and_isolated_from_trial_and_other_tenant(setup):
    db, tenants, admin = setup
    target, other = tenants
    grant(db, target, admin)
    read = ReadDb(tenants)
    future = NOW + timedelta(days=3650)
    summary = modulos_routes._assinatura_resumo_tenant(target, future)
    assert summary["acesso_completo_manual"] is True
    assert summary["acesso_completo_durante_trial"] is False
    assert summary["status"] == "trial"
    assert summary["status_efetivo"] == "expired"
    assert summary["trial_expirado"] is True
    assert summary["trial_fim"] == "2026-10-22T18:00:00Z"
    assert set(_load_active_modules(read, target.id, future)) == set(
        modulos_routes.MODULOS_TRIAL_COMPLETO
    )
    assert set(_load_active_entitlements(read, target.id, future)) == set(
        ALL_PUBLIC_ENTITLEMENTS
    )
    assert _load_active_modules(read, other.id, future) == []
    assert "veterinary.basic" not in _load_active_entitlements(read, other.id, future)
    target.modulos_ativos = '["fiscal", "bling"]'
    assert set(_load_active_modules(read, target.id, future)) == set(
        modulos_routes.MODULOS_PREMIUM
    )


@pytest.mark.parametrize(
    "billing", ["trial", "past_due", "blocked", "refunded", "canceled"]
)
def test_financial_state_does_not_remove_manual_grant_or_restore_sales_session_limits(
    setup, monkeypatch, billing
):
    db, (target, _), admin = setup
    grant(db, target, admin)
    target.billing_status = billing
    db.commit()
    monkeypatch.setattr(
        plan_limits,
        "monthly_sales_usage",
        lambda *_: pytest.fail("FULL nao tem limite de vendas"),
    )
    plan_limits.enforce_monthly_sales_limit(db, target.id, NOW)
    assert (
        plan_limits.enforce_simultaneous_session_limit(
            db, target, SimpleNamespace(token_jti="sessao-teste"), NOW
        )
        == 0
    )
    assert manual_full_access_allowed(target) is True
    assert modulos_routes._assinatura_resumo_tenant(target, NOW)["status"] == billing


@pytest.mark.parametrize("status", ["inactive", "suspended"])
def test_inactive_tenant_cannot_use_manual_full_access(setup, status):
    db, (target, _), admin = setup
    grant(db, target, admin)
    target.status = status
    db.commit()
    read = ReadDb([target])
    assert manual_full_access_allowed(target) is False
    assert _load_active_modules(read, target.id, NOW) == []
    assert _load_active_entitlements(read, target.id, NOW) == []
    with pytest.raises(HTTPException) as sales_error:
        plan_limits.enforce_monthly_sales_limit(db, target.id, NOW)
    assert sales_error.value.detail["code"] == "tenant_inactive"
    with pytest.raises(HTTPException) as sessions_error:
        plan_limits.enforce_simultaneous_session_limit(
            db, target, SimpleNamespace(token_jti="sessao-teste"), NOW
        )
    assert sessions_error.value.detail["code"] == "tenant_inactive"


def test_status_endpoint_exposes_manual_full_scope_and_unlimited_limits(
    setup, monkeypatch
):
    db, tenants, admin = setup
    target, _ = tenants
    grant(db, target, admin)
    monkeypatch.setattr(modulos_routes, "monthly_sales_usage", lambda *_: 1234)
    monkeypatch.setattr(modulos_routes, "active_session_usage", lambda *_: 8)
    result = modulos_routes.get_modulos_status((None, target.id), ReadDb(tenants))
    assert result["assinatura"]["acesso_completo_manual"] is True
    assert set(result["modulos_ativos"]) == set(modulos_routes.MODULOS_TRIAL_COMPLETO)
    assert set(result["recursos_ativos"]) == set(ALL_PUBLIC_ENTITLEMENTS)
    assert result["limites"]["aplicados"] == {
        "vendas_mensais": None,
        "acessos_simultaneos": None,
    }
    assert result["limites"]["apos_trial"]["vendas_mensais"] == 300
    assert result["uso"] == {"vendas_no_mes": 1234, "acessos_simultaneos": 8}


def test_grant_rejects_unknown_inactive_admin_and_empty_reason(setup):
    db, (target, _), admin = setup
    with pytest.raises(ManualFullAccessError) as error:
        grant_manual_full_access(
            db,
            tenant=target,
            actor_platform_admin_id=999,
            motivo="Motivo de teste completo.",
        )
    assert error.value.status_code == 403
    admin.is_active = False
    db.commit()
    with pytest.raises(ManualFullAccessError) as error:
        grant(db, target, admin)
    assert error.value.status_code == 403
    admin.is_active = True
    db.commit()
    with pytest.raises(ManualFullAccessError) as error:
        grant_manual_full_access(
            db, tenant=target, actor_platform_admin_id=admin.id, motivo="            "
        )
    assert error.value.status_code == 400
    assert target.manual_full_access is False


def test_rollback_undoes_grant_and_audit(setup):
    db, (target, _), admin = setup
    grant(db, target, admin, commit=False)
    db.rollback()
    db.refresh(target)
    assert target.manual_full_access is False
    with tenant_context(target.id):
        assert db.query(AuditLog).count() == 0


def test_route_rolls_back_grant_when_audit_cannot_be_recorded(setup, monkeypatch):
    db, (target, _), admin = setup
    monkeypatch.setattr(
        manual_full_access_service, "log_business_event", lambda **_: None
    )
    with pytest.raises(HTTPException) as error:
        ops_tenants_routes.liberar_acesso_completo_manual(
            tenant_id=UUID(target.id),
            payload=ops_tenants_routes.ManualFullAccessRequest(
                motivo="FULL permanente autorizado para esta empresa."
            ),
            current_admin=admin,
            db=db,
        )
    assert error.value.status_code == 500
    db.refresh(target)
    assert target.manual_full_access is False
    with tenant_context(target.id):
        assert db.query(AuditLog).count() == 0


def test_http_route_requires_actual_platform_session_and_records_only_target(setup):
    db, (target, other), admin = setup
    app = FastAPI()
    app.include_router(ops_tenants_routes.router)
    app.dependency_overrides[get_session] = lambda: db
    tenant_admin = User(id=7, email="cliente@example.test", is_admin=True)
    tenant_token = create_access_token(
        data={"sub": str(tenant_admin.id), "tenant_id": target.id, "jti": str(uuid4())}
    )
    admin_session = PlatformAdminSession(
        platform_admin_id=admin.id,
        token_jti=str(uuid4()),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        revoked=False,
    )
    db.add(admin_session)
    db.commit()
    platform_token = create_access_token(
        data={
            "sub": f"platform:{admin.id}",
            "scope": "platform_admin",
            "jti": admin_session.token_jti,
        }
    )
    url = f"/admin/tenants/{target.id}/acesso-completo/liberar"
    payload = {"motivo": "FULL permanente autorizado para esta empresa."}
    with TestClient(app) as client:
        assert client.post(url, json=payload).status_code in {401, 403}
        assert (
            client.post(
                url, json=payload, headers={"Authorization": f"Bearer {tenant_token}"}
            ).status_code
            == 401
        )
        assert target.manual_full_access is False
        response = client.post(
            url, json=payload, headers={"Authorization": f"Bearer {platform_token}"}
        )
    assert response.status_code == 200
    assert response.json()["acesso_completo_manual"] is True
    assert other.manual_full_access is False


def test_migration_defaults_existing_tenants_to_false_and_is_single_head(monkeypatch):
    backend = Path(__file__).resolve().parents[2]
    path = backend / "alembic/versions/zzzzn20261023a1_manual_full_access.py"
    spec = importlib.util.spec_from_file_location("manual_full_access_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    config = Config()
    config.set_main_option("script_location", str(backend / "alembic"))
    assert ScriptDirectory.from_config(config).get_heads() == [migration.revision]
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE tenants (id TEXT PRIMARY KEY)"))
        connection.execute(text("INSERT INTO tenants (id) VALUES ('existente')"))
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        assert (
            connection.execute(
                text("SELECT manual_full_access FROM tenants")
            ).scalar_one()
            == 0
        )
        migration.downgrade()
        assert [
            column["name"] for column in inspect(connection).get_columns("tenants")
        ] == ["id"]
    engine.dispose()
