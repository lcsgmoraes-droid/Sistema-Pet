"""Pacotes e caixas publicam o saldo compartilhado dos tubos, com reservas."""

from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.bling_estoque_sync import sincronizar_bling_background
from app import produto_identidade_models as _produto_identidade_models  # noqa: F401
from app.produtos_models import (
    Produto,
    ProdutoKitComponente,
    ProdutoBlingSync,
    ProdutoBlingSyncQueue,
)
from app.services import bling_sync_queue, bling_sync_reconciliation
from app.services.bling_sync_service import BlingSyncService
from app.services.bling_sync_stock import (
    estoque_produto_bling,
    estoques_produtos_bling,
    enfileirar_kits_dependentes,
)
from app.estoque_reserva_service import EstoqueReservaService
from app.tenancy.context import get_current_tenant, tenant_context


TENANT = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def stock_db():
    # Somente tabelas deste fluxo; nao depende do schema global de outros modulos.
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        for model in (
            Produto,
            ProdutoKitComponente,
            ProdutoBlingSync,
            ProdutoBlingSyncQueue,
        ):
            conn.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
    with tenant_context(TENANT), Session(engine) as db:
        yield db
    engine.dispose()


@pytest.fixture
def churu(stock_db, monkeypatch):
    db = stock_db
    tubo = Produto(
        tenant_id=TENANT,
        user_id=1,
        codigo="4000-1",
        nome="Churu tubo",
        tipo_produto="VARIACAO",
        estoque_atual=50,
    )
    pacote = Produto(
        tenant_id=TENANT,
        user_id=1,
        codigo="4000-4",
        nome="Churu pacote",
        tipo_produto="VARIACAO",
        tipo_kit="VIRTUAL",
        estoque_atual=-9,
    )
    caixa = Produto(
        tenant_id=TENANT,
        user_id=1,
        codigo="4000-24",
        nome="Churu caixa",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        estoque_atual=999,
    )
    db.add_all([tubo, pacote, caixa])
    db.flush()
    for kit, quantidade in [(pacote, 4), (caixa, 24)]:
        db.add(
            ProdutoKitComponente(
                tenant_id=TENANT,
                kit_id=kit.id,
                produto_componente_id=tubo.id,
                quantidade=quantidade,
            )
        )
        db.add(
            ProdutoBlingSync(
                tenant_id=TENANT,
                produto_id=kit.id,
                bling_produto_id=f"bling-{kit.codigo}",
                sincronizar=True,
            )
        )
    db.flush()
    monkeypatch.setattr(
        EstoqueReservaService,
        "mapa_reservas_ativas_por_produto",
        staticmethod(lambda session, tenant_id: {tubo.id: 3}),
    )
    return db, tubo, pacote, caixa


def test_virtual_stock_uses_free_components_and_ignores_cached_balance(churu):
    db, tubo, pacote, caixa = churu
    assert estoque_produto_bling(db, pacote, estoque_novo=400) == 11
    assert estoque_produto_bling(db, caixa) == 1
    assert estoque_produto_bling(db, tubo) == 50
    assert estoques_produtos_bling(db, [tubo, pacote, caixa], tenant_id=TENANT) == {
        tubo.id: 50,
        pacote.id: 11,
        caixa.id: 1,
    }
    assert (pacote.estoque_atual, caixa.estoque_atual) == (-9, 999)
    caixa.tipo_kit = "FISICO"
    assert estoque_produto_bling(db, caixa) == 999


def test_component_without_bling_link_queues_both_virtual_packages_atomically(churu):
    db, tubo, pacote, caixa = churu
    sincronizar_bling_background(tubo.id, 50, "entrada_nfe", db=db)
    assert db.query(ProdutoBlingSyncQueue).count() == 0
    db.commit()
    filas = (
        db.query(ProdutoBlingSyncQueue).order_by(ProdutoBlingSyncQueue.produto_id).all()
    )
    assert [(fila.produto_id, fila.estoque_novo) for fila in filas] == [
        (pacote.id, 11),
        (caixa.id, 1),
    ]
    assert all(fila.motivo == "entrada_nfe" for fila in filas)


def test_component_change_updates_existing_package_queues(churu):
    db, tubo, pacote, caixa = churu
    sincronizar_bling_background(tubo.id, 50, "entrada_nfe", db=db)
    tubo.estoque_atual = 26
    sincronizar_bling_background(tubo.id, 26, "venda", db=db)
    db.commit()
    filas = (
        db.query(ProdutoBlingSyncQueue).order_by(ProdutoBlingSyncQueue.produto_id).all()
    )
    assert [(fila.produto_id, fila.estoque_novo) for fila in filas] == [
        (pacote.id, 5),
        (caixa.id, 0),
    ]
    assert all(fila.motivo == "venda" for fila in filas)


def test_outer_rollback_discards_deferred_package_sync(churu):
    db, tubo, _pacote, _caixa = churu
    db.commit()
    tubo.estoque_atual = 26
    sincronizar_bling_background(tubo.id, 26, "venda", db=db)
    db.rollback()
    assert tubo.estoque_atual == 50
    assert "bling_kits_componentes_pendentes" not in db.info
    db.commit()
    assert db.query(ProdutoBlingSyncQueue).count() == 0


def test_deferred_package_sync_restores_source_tenant_at_commit(churu):
    db, tubo, pacote, caixa = churu
    sincronizar_bling_background(tubo.id, 50, "venda_compartilhada", db=db)
    tenant_da_venda = UUID("00000000-0000-0000-0000-000000000002")
    with tenant_context(tenant_da_venda):
        db.commit()
        assert get_current_tenant() == tenant_da_venda
    filas = (
        db.query(ProdutoBlingSyncQueue).order_by(ProdutoBlingSyncQueue.produto_id).all()
    )
    assert [(fila.produto_id, fila.estoque_novo) for fila in filas] == [
        (pacote.id, 11),
        (caixa.id, 1),
    ]


def test_package_queue_failure_preserves_committed_component_stock(churu, monkeypatch):
    db, tubo, _pacote, _caixa = churu
    db.commit()
    tubo.estoque_atual = 26
    sincronizar_bling_background(tubo.id, 26, "venda", db=db)

    def fail_dependents(*args, **kwargs):
        raise RuntimeError("Falha sintetica da fila de kits")

    monkeypatch.setattr(
        "app.services.bling_sync_stock.enfileirar_kits_dependentes", fail_dependents
    )
    db.commit()
    assert db.get(Produto, tubo.id).estoque_atual == 26
    assert db.query(ProdutoBlingSyncQueue).count() == 0


def test_background_commits_package_queues_without_component_link(churu, monkeypatch):
    db, tubo, pacote, caixa = churu
    commits = []
    monkeypatch.setattr(bling_sync_queue, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(db, "commit", lambda: commits.append(True) or db.flush())
    BlingSyncService.queue_product_sync_background(tubo.id, 50, "entrada_nfe")
    assert commits == [True]
    assert db.query(ProdutoBlingSyncQueue).count() == 2


def test_worker_recalculates_virtual_stock_after_further_component_sale(
    churu, monkeypatch
):
    db, tubo, pacote, _caixa = churu
    queued = BlingSyncService.queue_product_sync(db, pacote.id, estoque_novo=999)
    assert queued["estoque_enfileirado"] == 11
    tubo.estoque_atual = 42
    db.flush()
    sent = []
    monkeypatch.setattr(bling_sync_queue, "_reservar_janela_envio_bling", lambda: None)
    monkeypatch.setattr(
        bling_sync_queue,
        "BlingAPI",
        lambda: type(
            "Bling",
            (),
            {
                "atualizar_estoque_produto": staticmethod(
                    lambda **kwargs: sent.append(kwargs)
                )
            },
        )(),
    )
    result = BlingSyncService.process_queue_item_by_id(db, queued["queue_id"])
    assert result["ok"]
    assert result["estoque_enviado"] == 9
    assert sent[0]["estoque_novo"] == 9
    assert pacote.estoque_atual == -9


def test_reconciliation_compares_bling_with_virtual_stock(churu, monkeypatch):
    db, _tubo, pacote, _caixa = churu
    monkeypatch.setattr(bling_sync_reconciliation, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(db, "commit", lambda: db.flush())
    monkeypatch.setattr(
        bling_sync_reconciliation,
        "BlingAPI",
        lambda: type(
            "Bling",
            (),
            {
                "consultar_saldo_estoque": staticmethod(
                    lambda product_id: {"saldoFisicoTotal": 11}
                )
            },
        )(),
    )
    result = BlingSyncService.reconcile_product(pacote.id)
    assert result["ok"]
    assert result["estoque_sistema"] == 11
    assert result["divergencia"] == 0
    assert result["acao"] == "sem_acao"


def test_dependents_query_excludes_links_from_other_tenants(churu):
    db, tubo, pacote, caixa = churu
    outro_tenant = UUID("00000000-0000-0000-0000-000000000002")
    # Uma relacao corrompida de outro tenant nao pode publicar o kit local.
    db.connection().execute(
        ProdutoKitComponente.__table__.update().values(tenant_id=outro_tenant)
    )
    calls = []
    results = enfileirar_kits_dependentes(
        db,
        tubo.id,
        enfileirar=lambda *args, **kwargs: calls.append(kwargs) or {"ok": True},
    )
    assert results == []
    assert calls == []
