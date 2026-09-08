from uuid import uuid4

import pytest

from app.produtos_models import ProdutoBlingSyncQueue
from tests.unit.test_produto_alias_merge import case as _case_fixture, merge
from tests.unit.test_produto_alias_merge_api import api as _api_fixture

case = _case_fixture
api = _api_fixture


def path(product_id):
    return f"/estoque/sync/habilitacao/{product_id}"


def test_enablement_routes_are_registered_on_public_bling_router():
    from fastapi import FastAPI
    from app.bling_sync_routes import router

    application = FastAPI()
    application.include_router(router)
    paths = application.openapi()["paths"]
    assert {"get", "patch"}.issubset(paths[path("{produto_id}")])


@pytest.mark.parametrize("shared", [None, True, False])
def test_pause_resume_preserves_link_stock_and_nullable_policy(api, case, shared):
    client, _, _ = api
    case.a.estoque_compartilhado = shared
    case.db.commit()
    initial = client.get(path(case.primary.id))
    assert initial.status_code == 200
    assert initial.headers["Cache-Control"] == "no-store"
    assert initial.json()["estoque_compartilhado"] is shared
    for enabled in (False, False, True):
        result = client.patch(path(case.primary.id), json={"sincronizar": enabled})
        assert result.status_code == 200
        assert result.json()["sincronizar"] is enabled
        assert result.json()["estoque_compartilhado"] is shared
        assert result.json()["bling_produto_id"] == "BLING-A"
        assert case.primary.estoque_atual == 50
        assert case.primary.preco_custo == 49.94 and case.primary.preco_venda == 79.9
        assert case.db.query(ProdutoBlingSyncQueue).count() == 0


def test_pause_requires_auth_permission_and_current_tenant(api, case):
    client, app, state = api
    state["allow"] = False
    assert client.get(path(case.primary.id)).status_code == 403
    assert (
        client.patch(path(case.primary.id), json={"sincronizar": False}).status_code
        == 403
    )
    state["allow"] = True
    state["tenant"] = uuid4()
    assert client.get(path(case.primary.id)).status_code == 404
    assert (
        client.patch(path(case.primary.id), json={"sincronizar": False}).status_code
        == 404
    )
    assert case.a.sincronizar is True
    from app.auth.dependencies import get_current_user_and_tenant

    del app.dependency_overrides[get_current_user_and_tenant]
    assert client.patch(
        path(case.primary.id), json={"sincronizar": False}
    ).status_code in (401, 403)


def test_retired_origin_cannot_resume_even_if_flag_was_corrupted(api, case):
    client, _, _ = api
    merge(case)
    case.b.sincronizar = True
    case.db.commit()
    response = client.get(path(case.duplicate.id))
    assert response.json()["retirado"] is True
    assert (
        client.patch(path(case.duplicate.id), json={"sincronizar": True}).status_code
        == 409
    )
    assert case.b.retirado_para_produto_id == case.primary.id
    assert case.b.bling_produto_id == "BLING-B"


def test_missing_link_is_readable_but_never_autocreated(api, case):
    client, _, _ = api
    case.a.bling_produto_id = None
    case.db.commit()
    assert client.get(path(case.primary.id)).json()["vinculado"] is False
    assert (
        client.patch(path(case.primary.id), json={"sincronizar": True}).status_code
        == 409
    )
    assert case.a.bling_produto_id is None


def test_pause_payload_cannot_overwrite_inventory_or_nullable_policy(api, case):
    client, _, _ = api
    assert (
        client.patch(
            path(case.primary.id),
            json={"sincronizar": False, "estoque_compartilhado": True},
        ).status_code
        == 422
    )
    assert (
        client.patch(path(case.primary.id), json={"sincronizar": "false"}).status_code
        == 422
    )
    assert case.a.sincronizar is True
