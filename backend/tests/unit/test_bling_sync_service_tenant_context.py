from uuid import UUID
import inspect

import app.bling_sync_routes as bling_sync_routes
import app.services.bling_sync_auto_link as bling_sync_auto_link
import app.services.bling_sync_reconciliation as bling_sync_reconciliation
import app.services.bling_sync_service as bling_sync_service
import app.services.bling_sync_shared as bling_sync_shared
from app.services.bling_sync_service import BlingSyncService
from app.tenancy.context import clear_current_tenant, get_current_tenant


TENANT_A = UUID("11111111-1111-4111-8111-111111111111")
TENANT_B = UUID("22222222-2222-4222-8222-222222222222")
PREVIOUS_TENANT = UUID("99999999-9999-4999-8999-999999999999")


def teardown_function():
    clear_current_tenant()


def test_recent_reconcile_discovers_tenants_with_authorized_global_sql(monkeypatch):
    chamadas = []

    def fake_execute(db, sql, params=None, **kwargs):
        chamadas.append({"db": db, "sql": str(sql), "params": params or {}, **kwargs})
        return [(TENANT_A,), (TENANT_B,)]

    monkeypatch.setattr(bling_sync_shared, "execute_tenant_safe_all", fake_execute)

    db = object()
    resultado = bling_sync_service.listar_tenants_com_produto_bling_sync_recentes(
        db, minutes=45
    )

    assert resultado == [TENANT_A, TENANT_B]
    assert chamadas[0]["db"] is db
    assert "produto_bling_sync" in chamadas[0]["sql"]
    assert chamadas[0]["params"]["cutoff"]
    assert chamadas[0]["require_tenant"] is False
    assert chamadas[0]["allow_global"] is True
    assert "Bling produto recentes" in chamadas[0]["global_reason"]


def test_reconcile_recent_products_ativa_contexto_por_tenant(monkeypatch):
    vistos = []

    class FakeSession:
        def close(self):
            vistos.append(("close", get_current_tenant()))

    monkeypatch.setattr(
        bling_sync_reconciliation, "SessionLocal", lambda: FakeSession()
    )
    monkeypatch.setattr(
        bling_sync_reconciliation,
        "listar_tenants_com_produto_bling_sync_recentes",
        lambda *args, **kwargs: [TENANT_A, TENANT_B],
    )
    monkeypatch.setattr(
        BlingSyncService,
        "_listar_produto_ids_reconciliacao_recente",
        staticmethod(
            lambda db, tenant_id, **kwargs: (
                [101] if tenant_id == TENANT_A else [202, 203]
            )
        ),
    )

    def fake_reconcile(produto_id, force_sync=False):
        vistos.append((produto_id, force_sync, get_current_tenant()))
        return {"ok": True, "divergencia": 2.5 if produto_id == 202 else 0}

    monkeypatch.setattr(
        BlingSyncService, "reconcile_product", staticmethod(fake_reconcile)
    )

    resultado = BlingSyncService.reconcile_recent_products(minutes=30, limit=10)

    assert resultado["avaliados"] == 3
    assert resultado["divergencias"] == 1
    assert resultado["tenants_processados"] == 2
    assert vistos[:3] == [
        (101, False, TENANT_A),
        (202, False, TENANT_B),
        (203, False, TENANT_B),
    ]
    assert get_current_tenant() is None


def test_reconcile_all_products_ativa_contexto_por_tenant(monkeypatch):
    vistos = []

    class FakeSession:
        def close(self):
            vistos.append(("close", get_current_tenant()))

    monkeypatch.setattr(
        bling_sync_reconciliation, "SessionLocal", lambda: FakeSession()
    )
    monkeypatch.setattr(
        bling_sync_reconciliation,
        "listar_tenants_com_produto_bling_sync_ativo",
        lambda *args, **kwargs: [TENANT_A, TENANT_B],
    )
    monkeypatch.setattr(
        BlingSyncService,
        "_listar_produto_ids_reconciliacao_geral",
        staticmethod(
            lambda db, tenant_id, **kwargs: (
                [301, 302] if tenant_id == TENANT_A else [401]
            )
        ),
    )

    def fake_reconcile(produto_id, force_sync=False):
        vistos.append((produto_id, force_sync, get_current_tenant()))
        return {"ok": True, "divergencia": 0}

    monkeypatch.setattr(
        BlingSyncService, "reconcile_product", staticmethod(fake_reconcile)
    )

    resultado = BlingSyncService.reconcile_all_products(limit=2, force_sync=True)

    assert resultado["avaliados"] == 2
    assert resultado["tenants_processados"] == 1
    assert vistos[:2] == [
        (301, True, TENANT_A),
        (302, True, TENANT_A),
    ]
    assert get_current_tenant() is None


def test_auto_link_by_sku_global_ativa_contexto_por_tenant(monkeypatch):
    vistos = []

    class FakeSession:
        def close(self):
            vistos.append(("close", get_current_tenant()))

    monkeypatch.setattr(bling_sync_auto_link, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(
        bling_sync_auto_link,
        "listar_tenants_com_produtos_sem_vinculo_bling",
        lambda *args, **kwargs: [TENANT_A, TENANT_B],
    )

    def fake_auto_link(tenant_id, limit):
        vistos.append((tenant_id, limit, get_current_tenant()))
        return {"processados": 1, "vinculados": 1, "nao_encontrados": 0, "erros": 0}

    monkeypatch.setattr(
        BlingSyncService, "_auto_link_by_sku_for_tenant", staticmethod(fake_auto_link)
    )

    resultado = BlingSyncService.auto_link_by_sku(limit=3)

    assert resultado == {
        "processados": 2,
        "vinculados": 2,
        "nao_encontrados": 0,
        "erros": 0,
    }
    assert vistos == [
        ("close", None),
        (TENANT_A, 3, TENANT_A),
        (TENANT_B, 2, TENANT_B),
    ]
    assert get_current_tenant() is None


def test_rotas_manuais_de_reconciliacao_preservam_tenant_selecionado():
    recentes_source = inspect.getsource(bling_sync_routes.reconciliar_recentes)
    background_source = inspect.getsource(
        bling_sync_routes._executar_reconciliacao_geral_em_background
    )
    geral_source = inspect.getsource(bling_sync_routes.reconciliar_geral)

    assert "tenant_id=tenant_id" in recentes_source
    assert "tenant_id=tenant_id" in background_source
    assert "args=(limite, tenant_id)" in geral_source
