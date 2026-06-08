import os
from datetime import date
from types import SimpleNamespace

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.produtos.lotes import _consumir_lotes_fifo_produto


def test_consumir_lotes_fifo_produto_consume_parcialmente_primeiro_lote():
    lote_a = SimpleNamespace(
        id=1,
        nome_lote="A",
        quantidade_disponivel=10,
        data_validade=date(2026, 7, 10),
    )
    lote_b = SimpleNamespace(
        id=2,
        nome_lote="B",
        quantidade_disponivel=8,
        data_validade=None,
    )

    consumidos = _consumir_lotes_fifo_produto([lote_a, lote_b], 4)

    assert consumidos == [
        {
            "lote_id": 1,
            "nome_lote": "A",
            "quantidade_consumida": 4,
            "data_validade": "2026-07-10",
        }
    ]
    assert lote_a.quantidade_disponivel == 6
    assert lote_b.quantidade_disponivel == 8


def test_consumir_lotes_fifo_produto_avanca_para_proximo_lote():
    lote_a = SimpleNamespace(
        id=1,
        nome_lote="A",
        quantidade_disponivel=3,
        data_validade=None,
    )
    lote_b = SimpleNamespace(
        id=2,
        nome_lote="B",
        quantidade_disponivel=8,
        data_validade=date(2026, 8, 5),
    )

    consumidos = _consumir_lotes_fifo_produto([lote_a, lote_b], 5)

    assert consumidos == [
        {
            "lote_id": 1,
            "nome_lote": "A",
            "quantidade_consumida": 3,
            "data_validade": None,
        },
        {
            "lote_id": 2,
            "nome_lote": "B",
            "quantidade_consumida": 2,
            "data_validade": "2026-08-05",
        },
    ]
    assert lote_a.quantidade_disponivel == 0
    assert lote_b.quantidade_disponivel == 6


def test_consumir_lotes_fifo_produto_ignora_quantidade_zero():
    lote = SimpleNamespace(
        id=1,
        nome_lote="A",
        quantidade_disponivel=3,
        data_validade=None,
    )

    assert _consumir_lotes_fifo_produto([lote], 0) == []
    assert lote.quantidade_disponivel == 3
