from decimal import Decimal

from app.estoque.service import (
    _normalizar_quantidade_estoque,
    _somar_quantidade_estoque,
)


def test_somar_quantidade_estoque_aceita_decimal_vindo_de_item_de_venda():
    assert _somar_quantidade_estoque(1.0, Decimal("2.5")) == 3.5


def test_normalizar_quantidade_estoque_trata_none_como_zero():
    assert _normalizar_quantidade_estoque(None) == 0.0
