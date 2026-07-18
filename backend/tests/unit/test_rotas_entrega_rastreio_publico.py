from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints import rotas_entrega_public_routes
from app.db import get_session
from app.tenancy.context import clear_current_tenant, get_current_tenant


def test_endpoint_de_rastreio_publico_nao_exige_login(monkeypatch):
    app = FastAPI()
    app.include_router(rotas_entrega_public_routes.router)
    app.dependency_overrides[get_session] = lambda: object()
    monkeypatch.setattr(
        rotas_entrega_public_routes,
        "montar_rastreio_publico",
        lambda _db, token: {"token": token, "status": "em_rota"},
    )

    response = TestClient(app).get("/rotas-entrega/rastreio/token-seguro")

    assert response.status_code == 200
    assert response.json() == {"token": "token-seguro", "status": "em_rota"}


def test_router_publico_e_registrado_fora_da_protecao_do_modulo():
    fonte = Path("app/main_routers.py").read_text(encoding="utf-8")
    include_publico = fonte.index("app.include_router(rotas_entrega_public_router)")
    include_privado = fonte.index("        rotas_entrega_router,")

    assert include_publico < include_privado


def test_token_ativa_somente_o_tenant_encontrado_e_restaura_contexto(monkeypatch):
    from app.api.endpoints import rotas_entrega_tracking

    tenant_id = UUID("00000000-0000-0000-0000-000000000123")
    indice = SimpleNamespace(tenant_id=tenant_id, rota_id=77)
    monkeypatch.setattr(
        rotas_entrega_tracking,
        "_buscar_indice_rastreio",
        lambda _db, _token: indice,
    )

    observado = {}

    def montar(_db, *, rota_id_indice, tenant_id):
        observado["rota_id"] = rota_id_indice
        observado["tenant_param"] = tenant_id
        observado["tenant_contexto"] = get_current_tenant()
        return {"ok": True}

    monkeypatch.setattr(
        rotas_entrega_tracking,
        "_montar_rastreio_publico_tenant",
        montar,
    )
    clear_current_tenant()

    assert rotas_entrega_tracking.montar_rastreio_publico(object(), "token") == {
        "ok": True
    }
    assert observado == {
        "rota_id": 77,
        "tenant_param": tenant_id,
        "tenant_contexto": tenant_id,
    }
    assert get_current_tenant() is None
