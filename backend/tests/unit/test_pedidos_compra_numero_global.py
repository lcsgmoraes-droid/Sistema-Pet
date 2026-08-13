from app.pedidos_compra.core_routes import (
    _numero_pedido_definitivo,
    _numero_pedido_temporario,
)


def test_numero_temporario_e_globalmente_unico():
    primeiro = _numero_pedido_temporario()
    segundo = _numero_pedido_temporario()

    assert primeiro.startswith("TMP-")
    assert segundo.startswith("TMP-")
    assert primeiro != segundo


def test_numero_definitivo_usa_id_global_do_pedido():
    assert _numero_pedido_definitivo(1, ano=2026) == "PC202600001"
    assert _numero_pedido_definitivo(4812, ano=2026) == "PC202604812"
