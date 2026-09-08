"""A fila do Bling respeita a transação de estoque recebida pelo wrapper."""

import pytest
from sqlalchemy import Column, Float, Integer, MetaData, Table, create_engine, select
from sqlalchemy.orm import Session

from app.bling_estoque_sync import sincronizar_bling_background
from app.services.bling_sync_service import BlingSyncService


@pytest.fixture
def transaction_case():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    stock = Table(
        "test_stock",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("saldo", Float),
    )
    queue = Table(
        "test_queue",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("saldo", Float),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(stock.insert().values(id=1, saldo=50))
    with Session(engine) as db:
        yield db, stock, queue
    engine.dispose()


def test_queue_savepoint_failure_preserves_outer_stock_transaction(
    transaction_case, monkeypatch
):
    db, stock, queue = transaction_case
    db.execute(stock.update().values(saldo=49))

    def fail_queue(received_db, **kwargs):
        assert received_db is db
        db.execute(queue.insert().values(id=1, saldo=kwargs["estoque_novo"]))
        raise RuntimeError("Falha sintética ao montar a fila")

    monkeypatch.setattr(BlingSyncService, "queue_product_sync", fail_queue)
    sincronizar_bling_background(1, 49, "venda", db=db)

    assert db.in_transaction()
    assert db.connection().execute(select(stock.c.saldo)).scalar_one() == 49
    assert db.connection().execute(select(queue.c.id)).all() == []
    db.commit()
    assert db.connection().execute(select(stock.c.saldo)).scalar_one() == 49


def test_queue_savepoint_success_is_rolled_back_with_stock(
    transaction_case, monkeypatch
):
    db, stock, queue = transaction_case
    db.execute(stock.update().values(saldo=49))

    def enqueue(received_db, **kwargs):
        assert received_db is db
        db.execute(queue.insert().values(id=1, saldo=kwargs["estoque_novo"]))
        return {"ok": True}

    def forbid_separate_session(**kwargs):
        raise AssertionError("Uma venda aberta não pode enfileirar em outra sessão")

    monkeypatch.setattr(BlingSyncService, "queue_product_sync", enqueue)
    monkeypatch.setattr(
        BlingSyncService, "queue_product_sync_background", forbid_separate_session
    )
    sincronizar_bling_background(1, 49, "venda", db=db)

    assert db.in_transaction()
    assert db.connection().execute(select(queue.c.saldo)).scalar_one() == 49
    db.rollback()
    assert db.connection().execute(select(stock.c.saldo)).scalar_one() == 50
    assert db.connection().execute(select(queue.c.id)).all() == []


def test_committed_stock_event_preserves_separate_session_path(monkeypatch):
    calls = []
    monkeypatch.setattr(
        BlingSyncService,
        "queue_product_sync_background",
        lambda **kwargs: calls.append(kwargs),
    )
    sincronizar_bling_background(4752, 49, "entrada_confirmada")
    assert calls == [
        {
            "produto_id": 4752,
            "estoque_novo": 49,
            "motivo": "entrada_confirmada",
            "origem": "evento",
        }
    ]
