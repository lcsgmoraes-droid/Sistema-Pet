from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from app import main_background_jobs
from app.tenancy.context import get_current_tenant


def test_bootstrap_migra_token_legado_para_tenant(monkeypatch):
    tenant_id = uuid4()
    saved = {}
    monkeypatch.setenv("BLING_WEBHOOK_TENANT_ID", str(tenant_id))
    monkeypatch.setattr(
        "app.services.bling_connection_service.get_bling_connection",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.bling_integration_parts.core._load_bling_runtime_config",
        lambda: {
            "source": "legacy",
            "access_token": "access-antigo",
            "refresh_token": "refresh-antigo",
        },
    )
    monkeypatch.setattr(
        "app.services.bling_connection_service.save_bling_tokens",
        lambda **kwargs: saved.update(kwargs),
    )

    assert main_background_jobs._bootstrap_conexao_bling_legada() is True
    assert saved == {
        "tenant_id": str(tenant_id),
        "access_token": "access-antigo",
        "refresh_token": "refresh-antigo",
        "expires_in": 60,
    }
    assert get_current_tenant() is None


def test_renovacao_pula_token_fresco_e_renova_token_proximo(monkeypatch):
    fresh_tenant = uuid4()
    due_tenant = uuid4()
    renewed = []
    now = datetime.now(timezone.utc)
    connections = {
        fresh_tenant: SimpleNamespace(expires_at=now + timedelta(hours=4)),
        due_tenant: SimpleNamespace(expires_at=now + timedelta(minutes=30)),
    }

    monkeypatch.delenv("BLING_WEBHOOK_TENANT_ID", raising=False)
    monkeypatch.setattr(
        main_background_jobs, "_bootstrap_conexao_bling_legada", lambda: False
    )
    monkeypatch.setattr(
        "app.services.bling_connection_service.connected_bling_tenant_ids",
        lambda: [fresh_tenant, due_tenant],
    )
    monkeypatch.setattr(
        "app.services.bling_connection_service.get_bling_connection",
        lambda tenant_id: connections[UUID(str(tenant_id))],
    )

    class FakeBlingAPI:
        def renovar_access_token(self):
            renewed.append(get_current_tenant())

    monkeypatch.setattr("app.bling_integration.BlingAPI", FakeBlingAPI)

    summary = main_background_jobs._renovar_conexoes_bling()

    assert summary == {"renovadas": 1, "adiadas": 1, "falhas": 0}
    assert renewed == [due_tenant]
    assert get_current_tenant() is None
