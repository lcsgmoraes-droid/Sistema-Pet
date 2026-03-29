from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.estoque_reserva_service import EstoqueReservaService


def test_skus_produto_inclui_codigo_e_codigo_barras_sem_duplicar():
    produto = SimpleNamespace(codigo="SKU-1", codigo_barras="789123")

    skus = EstoqueReservaService._skus_produto(produto)

    assert skus == ["SKU-1", "789123"]


def test_skus_produto_remove_alias_vazio_e_duplicado():
    produto = SimpleNamespace(codigo="SKU-1", codigo_barras="SKU-1")

    skus = EstoqueReservaService._skus_produto(produto)

    assert skus == ["SKU-1"]


def test_mapa_reservas_ativas_por_produto_desloca_kit_virtual_para_componentes():
    item = SimpleNamespace(sku="KIT-1", quantidade=2)
    kit = SimpleNamespace(id=10, codigo="KIT-1", codigo_barras=None, tipo_produto="KIT", tipo_kit="VIRTUAL")
    componente = SimpleNamespace(kit_id=10, produto_componente_id=20, quantidade=1.5)

    with patch.object(EstoqueReservaService, "_itens_reservados_ativos", return_value=[item]), patch.object(
        EstoqueReservaService,
        "_produtos_por_sku",
        return_value={"KIT-1": kit},
    ), patch.object(
        EstoqueReservaService,
        "_componentes_por_kit",
        return_value={10: [componente]},
    ):
        reservas = EstoqueReservaService.mapa_reservas_ativas_por_produto(db=Mock(), tenant_id="tenant-1")

    assert reservas == {20: 3.0}


def test_reservar_kit_virtual_valida_estoque_no_componente():
    db = Mock()
    produto_kit = SimpleNamespace(id=10, codigo="KIT-1", codigo_barras=None, nome="Kit", tipo_produto="KIT", tipo_kit="VIRTUAL")
    produto_componente = SimpleNamespace(id=20, codigo="COMP-1", nome="Componente", estoque_atual=5)
    item = SimpleNamespace(tenant_id="tenant-1", sku="KIT-1", quantidade=2)

    query_produto = Mock()
    query_produto.filter.return_value.first.side_effect = [produto_kit, produto_componente]
    db.query.return_value = query_produto

    with patch.object(
        EstoqueReservaService,
        "mapa_reservas_ativas_por_produto",
        return_value={20: 1.0},
    ), patch.object(
        EstoqueReservaService,
        "_componentes_por_kit",
        return_value={10: [SimpleNamespace(produto_componente_id=20, quantidade=2)]},
    ):
        reservado = EstoqueReservaService.reservar(db, item)

    assert reservado is True
