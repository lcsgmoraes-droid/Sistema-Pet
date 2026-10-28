from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.security import module_access


class _TrialQuery:
    def __init__(self, model, tenant, modules=None):
        self.model = model
        self.tenant = tenant
        self.modules = modules or []

    def filter(self, *criteria):
        self.criteria = criteria
        return self

    def first(self):
        if self.model is module_access.Tenant:
            return self.tenant
        return None

    def all(self):
        return self.modules


class _TrialDb:
    def __init__(self, tenant, modules=None):
        self.tenant = tenant
        self.modules = modules or []

    def query(self, model):
        return _TrialQuery(model, self.tenant, self.modules)


def _user(**overrides):
    data = {
        "is_superadmin": False,
        "is_system_admin": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _credentials():
    return SimpleNamespace(credentials="token-teste")


def _client_com_modulo_bling(path: str) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[module_access.get_session] = lambda: object()

    @app.post(
        path, dependencies=[Depends(module_access.require_active_module("bling"))]
    )
    def endpoint_teste():
        return {"status": "ok"}

    return TestClient(app)


def _patch_auth(monkeypatch, user, tenant_id):
    monkeypatch.setattr(
        module_access, "get_current_user", lambda credentials, session: user
    )

    async def fake_get_current_user_and_tenant(credentials, user, db):
        return user, tenant_id

    monkeypatch.setattr(
        module_access,
        "get_current_user_and_tenant",
        fake_get_current_user_and_tenant,
    )


def test_load_active_modules_libera_experiencia_completa_durante_trial():
    agora = datetime(2026, 7, 18, tzinfo=timezone.utc)
    tenant = SimpleNamespace(
        plan="pet-start",
        modulos_ativos="[]",
        billing_status="trial",
        trial_started_at=agora,
        trial_ends_at=agora + timedelta(days=30),
        subscription_source="manual",
        subscription_activated_at=None,
    )

    ativos = module_access._load_active_modules(_TrialDb(tenant), "tenant-1", agora)

    assert "compras" in ativos
    assert "veterinario" in ativos
    assert "banho_tosa" in ativos
    assert "bling" not in ativos


def test_modulo_extra_da_proposta_continua_apos_quinze_dias():
    tenant = SimpleNamespace(
        plan="pet-start",
        modulos_ativos="[]",
        billing_status="past_due",
        billing_next_due_date=datetime(2026, 7, 1).date(),
        trial_ends_at=None,
    )
    extra = SimpleNamespace(modulo="veterinario", gateway="asaas_offer", data_fim=None)
    db = _TrialDb(tenant, [extra])

    assert "veterinario" in module_access._load_active_modules(
        db, "tenant-1", datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    )
    assert "veterinario" in module_access._load_active_modules(
        db, "tenant-1", datetime(2026, 7, 17, 12, tzinfo=timezone.utc)
    )


@pytest.mark.parametrize("billing", ["trial", "expired"])
def test_trial_vencido_preserva_todos_modulos_ate_revisao(billing):
    now = datetime(2026, 7, 18, tzinfo=timezone.utc)
    tenant = SimpleNamespace(
        status="active",
        plan="pet-start",
        modulos_ativos="[]",
        billing_status=billing,
        trial_started_at=now - timedelta(days=31),
        trial_ends_at=now - timedelta(days=1),
    )

    active = module_access._load_active_modules(_TrialDb(tenant), "tenant-1", now)

    assert "veterinario" in active
    assert "banho_tosa" in active
    assert "compras" in active


@pytest.mark.parametrize("status", ["suspended", "inactive"])
def test_suspensao_manual_retira_modulos_inclusive_trial_e_extra(status):
    now = datetime(2026, 7, 18, tzinfo=timezone.utc)
    tenant = SimpleNamespace(
        status=status,
        plan="pet-gestao",
        modulos_ativos='["entregas"]',
        billing_status="trial",
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=30),
    )
    extra = SimpleNamespace(modulo="veterinario", gateway="asaas_offer", data_fim=None)
    db = _TrialDb(tenant, [extra])

    assert module_access._load_active_modules(db, "tenant-1", now) == []
    assert module_access._load_active_entitlements(db, "tenant-1", now) == []


@pytest.mark.parametrize(
    "plano_legado", ["premium", "completo", "full", "free", "legado"]
)
def test_load_active_entitlements_libera_plano_legado_sem_segmento(plano_legado):
    """Regressao: tenant com `plan` legado (premium/completo/full/free/legado)
    e plan_pet/vet/grooming vazios ficava com ZERO entitlements, porque
    get_plan() nunca resolve esses codigos - mesmo com acesso operacional
    liberado. Era a causa do erro "recurso nao incluido no plano atual" na
    Central NF-e Entradas pra esses tenants (ver _entitlements_plano_legado)."""
    agora = datetime(2026, 7, 18, tzinfo=timezone.utc)
    tenant = SimpleNamespace(
        plan=plano_legado,
        plan_pet=None,
        plan_vet=None,
        plan_grooming=None,
        billing_status="active",
        trial_ends_at=None,
        subscription_source="manual",
        subscription_activated_at=None,
    )

    entitlements = module_access._load_active_entitlements(
        _TrialDb(tenant), "tenant-1", agora
    )

    assert "purchases.invoice_xml" in entitlements
    assert "finance.management" in entitlements


def test_load_active_entitlements_plano_real_do_catalogo_nao_ganha_tudo():
    """Plano real do catalogo (nao legado) deve continuar restrito aos
    proprios entitlements - a correcao e so pro fallback de plano legado."""
    agora = datetime(2026, 7, 18, tzinfo=timezone.utc)
    tenant = SimpleNamespace(
        plan="pet-basico",
        plan_pet="pet-basico",
        plan_vet=None,
        plan_grooming=None,
        billing_status="active",
        trial_ends_at=None,
        subscription_source="manual",
        subscription_activated_at=None,
    )

    entitlements = module_access._load_active_entitlements(
        _TrialDb(tenant), "tenant-1", agora
    )

    assert "purchases.invoice_xml" in entitlements  # pet-basico ja inclui isso
    assert "finance.management" not in entitlements  # mas nao o bundle inteiro


@pytest.mark.asyncio
async def test_require_active_module_blocks_tenant_without_module(monkeypatch):
    user = _user()
    _patch_auth(monkeypatch, user, "tenant-1")
    monkeypatch.setattr(module_access, "_load_active_modules", lambda db, tenant_id: [])

    dependency = module_access.require_active_module("compras")

    with pytest.raises(HTTPException) as exc:
        await dependency(credentials=_credentials(), db=object())

    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "module_not_enabled"
    assert exc.value.detail["modulo"] == "compras"


@pytest.mark.asyncio
async def test_require_active_module_allows_tenant_with_module(monkeypatch):
    user = _user()
    _patch_auth(monkeypatch, user, "tenant-1")
    monkeypatch.setattr(
        module_access, "_load_active_modules", lambda db, tenant_id: ["compras"]
    )

    dependency = module_access.require_active_module("compras")

    assert await dependency(credentials=_credentials(), db=object()) is None


@pytest.mark.asyncio
async def test_require_active_module_superadmin_bypasses_plan(monkeypatch):
    user = _user(is_superadmin=True)
    _patch_auth(monkeypatch, user, "tenant-1")

    def fail_if_called(db, tenant_id):  # pragma: no cover - should not run
        raise AssertionError("superadmin should not query tenant module plan")

    monkeypatch.setattr(module_access, "_load_active_modules", fail_if_called)

    dependency = module_access.require_active_module("compras")

    assert await dependency(credentials=_credentials(), db=object()) is None


@pytest.mark.asyncio
async def test_require_active_module_requires_tenant_context(monkeypatch):
    user = _user()
    _patch_auth(monkeypatch, user, None)
    monkeypatch.setattr(
        module_access, "_load_active_modules", lambda db, tenant_id: ["compras"]
    )

    dependency = module_access.require_active_module("compras")

    with pytest.raises(HTTPException) as exc:
        await dependency(credentials=_credentials(), db=object())

    assert exc.value.status_code == 403
    assert exc.value.detail == "Tenant obrigatorio para acessar este modulo"


@pytest.mark.asyncio
async def test_require_active_module_rejects_missing_credentials():
    dependency = module_access.require_active_module("compras")

    with pytest.raises(HTTPException) as exc:
        await dependency(credentials=None, db=object())

    assert exc.value.status_code == 403
    assert exc.value.detail == "Not authenticated"


@pytest.mark.parametrize("path", ["/integracoes/bling/pedido", "/integracoes/bling/nf"])
def test_require_active_module_allows_public_bling_webhooks_without_credentials(path):
    client = _client_com_modulo_bling(path)

    response = client.post(path)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_require_active_module_keeps_other_bling_routes_private_without_credentials():
    client = _client_com_modulo_bling("/integracoes/bling/pedidos")

    response = client.post("/integracoes/bling/pedidos")

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_require_active_module_rejects_unknown_module():
    with pytest.raises(ValueError, match="Modulo comercial desconhecido"):
        module_access.require_active_module("modulo_fantasma")
