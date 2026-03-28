from types import SimpleNamespace

from app.estoque_reserva_service import EstoqueReservaService


def test_skus_produto_inclui_codigo_e_codigo_barras_sem_duplicar():
    produto = SimpleNamespace(codigo="SKU-1", codigo_barras="789123")

    skus = EstoqueReservaService._skus_produto(produto)

    assert skus == ["SKU-1", "789123"]


def test_skus_produto_remove_alias_vazio_e_duplicado():
    produto = SimpleNamespace(codigo="SKU-1", codigo_barras="SKU-1")

    skus = EstoqueReservaService._skus_produto(produto)

    assert skus == ["SKU-1"]
