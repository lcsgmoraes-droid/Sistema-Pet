from app.pedidos_compra.quantidades import (
    calcular_quantidade_total_unidades,
    formatar_quantidade_compra_documento,
    normalizar_quantidade_por_embalagem,
    normalizar_unidade_compra,
)
from app.pedidos_compra.schemas import PedidoCompraItemRequest


def test_formata_quantidade_compra_com_embalagem_e_total_em_unidades():
    assert normalizar_unidade_compra("cx") == "CX"
    assert normalizar_quantidade_por_embalagem("CX", 12) == 12
    assert calcular_quantidade_total_unidades(2, "CX", 12) == 24
    assert formatar_quantidade_compra_documento(2, "CX", 12) == "2 CX (24 unid)"


def test_formata_quantidade_unitaria_sem_total_duplicado():
    assert normalizar_quantidade_por_embalagem("UN", 12) == 1
    assert calcular_quantidade_total_unidades(12, "UN", 12) == 12
    assert formatar_quantidade_compra_documento(12, "UN", 12) == "12 UN"


def test_schema_item_pedido_guarda_unidade_compra_e_embalagem():
    item = PedidoCompraItemRequest(
        produto_id=10,
        quantidade_pedida=2,
        preco_unitario=4.5,
        unidade_compra="FD",
        quantidade_por_embalagem=24,
    )

    assert item.unidade_compra == "FD"
    assert item.quantidade_por_embalagem == 24


def test_embalagem_pode_ficar_sem_fator_sem_gerar_total_falso():
    item = PedidoCompraItemRequest(
        produto_id=10,
        quantidade_pedida=2,
        preco_unitario=4.5,
        unidade_compra="CX",
        quantidade_por_embalagem=None,
    )

    assert item.unidade_compra == "CX"
    assert item.quantidade_por_embalagem is None
    assert normalizar_quantidade_por_embalagem("CX", None) is None
    assert calcular_quantidade_total_unidades(2, "CX", None) == 2
    assert formatar_quantidade_compra_documento(2, "CX", None) == "2 CX"
