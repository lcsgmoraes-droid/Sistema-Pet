from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produto_identity_models import ProdutoFusaoLog, ProdutoSkuAlias
from app.produtos.aliases_sku_routes import router as alias_router
from app.produtos.variacoes_fusao_routes import router as merge_router
from app.produtos.cadastro_routes import router as cadastro_router
from app.security import permissions_decorator
from tests.unit.test_produto_alias_merge import case as _case_fixture
from tests.unit.test_produto_alias_merge import merge
from app.produtos_models import Produto

case = _case_fixture


@pytest.fixture
def api(case, monkeypatch):
    app = FastAPI()
    app.include_router(alias_router, prefix="/produtos")
    app.include_router(merge_router, prefix="/produtos")
    app.include_router(cadastro_router, prefix="/produtos")
    app.dependency_overrides[get_session] = lambda: case.db
    state = {"tenant": case.tenant, "allow": True}

    def auth():
        return SimpleNamespace(id=1), state["tenant"]

    app.dependency_overrides[get_current_user_and_tenant] = auth

    def permission(db, user_id, permission, tenant_id, **kwargs):
        assert permission in {"produtos.editar", "produtos.criar"}
        assert user_id == 1 and tenant_id == state["tenant"]
        if not state["allow"]:
            raise HTTPException(status_code=403, detail="Permissao negada")

    monkeypatch.setattr(permissions_decorator, "check_permission", permission)
    with TestClient(app) as client:
        yield client, app, state


def test_alias_requires_auth_and_product_edit_permission(api, case):
    client, app, state = api
    state["allow"] = False
    route = f"/produtos/{case.primary.id}/aliases-sku/preview"
    assert client.post(route, json={"sku": "NEW"}).status_code == 403
    del app.dependency_overrides[get_current_user_and_tenant]
    assert client.post(route, json={"sku": "NEW"}).status_code in (401, 403)
    assert case.db.query(ProdutoSkuAlias).count() == 0


def test_alias_preview_apply_and_stale_replay(api, case):
    client, _, _ = api
    route = f"/produtos/{case.primary.id}/aliases-sku"
    preview = client.post(route + "/preview", json={"sku": "OLD"})
    assert preview.status_code == 200
    body = {
        "sku": "OLD",
        "motivo": "Identidade confirmada pelo responsavel.",
        "preview_token": preview.json()["preview_token"],
    }
    assert case.db.query(ProdutoSkuAlias).count() == 0
    assert client.post(route + "/aplicar", json=body).status_code == 200
    assert client.post(route + "/aplicar", json=body).status_code == 409
    assert case.db.query(ProdutoSkuAlias).count() == 1
    assert case.primary.estoque_atual == 50


def test_other_tenant_cannot_preview_or_mutate_known_id(api, case):
    client, _, state = api
    state["tenant"] = uuid4()
    response = client.post(
        f"/produtos/{case.primary.id}/aliases-sku/preview", json={"sku": "NEW"}
    )
    assert response.status_code == 400
    response = client.post(
        "/produtos/fusao/preview",
        json={
            "produto_principal_id": case.primary.id,
            "produto_duplicado_id": case.duplicate.id,
        },
    )
    assert response.status_code == 400


def test_merge_error_rolls_back_alias_stock_archive_and_retirement(
    api, case, monkeypatch
):
    from app.services import produto_merge_service

    client, _, _ = api
    body = {
        "produto_principal_id": case.primary.id,
        "produto_duplicado_id": case.duplicate.id,
        "estrategia_estoque": "manter_principal",
    }
    preview = client.post("/produtos/fusao/preview", json=body)
    assert preview.status_code == 200

    def fail(*args, **kwargs):
        raise RuntimeError("Falha de auditoria simulada")

    monkeypatch.setattr(produto_merge_service, "record_merge", fail)
    response = client.post(
        "/produtos/fusao/executar",
        json=body
        | {
            "preview_token": preview.json()["preview_token"],
            "preservar_vinculo_bling_duplicado": True,
            "aliases_sku": ["SELLER-OLD"],
            "observacao": "Estoque fisico total conferido em cinquenta unidades.",
        },
    )
    assert response.status_code == 500
    case.db.expire_all()
    assert case.primary.estoque_atual == 50 and case.duplicate.estoque_atual == 4
    assert case.duplicate.deleted_at is None
    assert case.b.sincronizar and case.b.retirado_para_produto_id is None
    assert case.db.query(ProdutoSkuAlias).count() == 0
    assert case.db.query(ProdutoFusaoLog).count() == 0


def test_create_and_rename_cannot_reuse_preserved_sku(api, case):
    client, _, _ = api
    third = Produto(
        tenant_id=case.tenant,
        user_id=1,
        codigo="THIRD",
        nome="Other",
        tipo="produto",
        tipo_produto="SIMPLES",
        preco_venda=10,
    )
    case.db.add(third)
    case.db.commit()
    merge(case)
    created = client.post(
        "/produtos/", json={"codigo": "ANTIGO", "nome": "New item", "preco_venda": 10}
    )
    assert created.status_code == 400 and "alias" in created.json()["detail"]
    renamed = client.put(f"/produtos/{third.id}", json={"codigo": "ANTIGO"})
    assert renamed.status_code == 400 and "alias" in renamed.json()["detail"]
    assert case.db.query(Produto).count() == 3
    assert third.codigo == "THIRD"


def test_barcode_or_alternate_code_cannot_collide_with_preserved_sku(api, case):
    client, _, _ = api
    merge(case)
    for field, value in (
        ("codigo_barras", "ANTIGO"),
        ("codigos_barras_alternativos", '["ANTIGO"]'),
    ):
        response = client.post(
            "/produtos/",
            json={
                "codigo": "DIFFERENT",
                "nome": "Other",
                "preco_venda": 10,
                field: value,
            },
        )
        assert response.status_code == 400 and "alias" in response.json()["detail"]
