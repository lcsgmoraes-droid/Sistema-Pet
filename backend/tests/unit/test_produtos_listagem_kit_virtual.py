from types import SimpleNamespace
from unittest.mock import patch

from app import produtos_routes


def test_listagem_calcula_estoque_virtual_mesmo_sem_detalhes_do_kit():
    db = object()
    produto = SimpleNamespace(
        id=6936,
        tenant_id="tenant-1",
        tipo_produto="VARIACAO",
        tipo_kit="VIRTUAL",
        estoque_atual=-1,
        categoria=None,
        preco_venda=59.90,
        preco_promocional=None,
        promocao_inicio=None,
        promocao_fim=None,
    )

    with patch.object(
        produtos_routes.KitEstoqueService,
        "calcular_estoque_virtual_kit",
        return_value=31,
    ) as calcular_estoque_virtual:
        resultado = produtos_routes._enriquecer_produto_listagem(
            db,
            produto,
            tenant_id="tenant-1",
            reservas_por_produto={},
            incluir_detalhes_composto=False,
        )

    calcular_estoque_virtual.assert_called_once_with(
        db,
        produto.id,
        tenant_id=produto.tenant_id,
        reservas_por_produto={},
    )
    assert resultado.composicao_kit == []
    assert resultado.estoque_virtual == 31
    assert resultado.estoque_disponivel == 31
