from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from app.produtos.listagem import (
    enriquecer_preco_pdv,
    enriquecer_produto_listagem,
    resolver_promocao_erp_produto,
)


def test_modulo_listagem_resolve_promocao_erp_ativa():
    agora = datetime(2026, 5, 25, 10, 0)
    produto = SimpleNamespace(
        preco_venda=100,
        preco_promocional=80,
        promocao_inicio=agora - timedelta(days=1),
        promocao_fim=agora + timedelta(days=1),
    )

    promocao = resolver_promocao_erp_produto(produto, referencia=agora)

    assert promocao == {
        "promocao_ativa": True,
        "preco_pdv": 80.0,
        "preco_regular": 100.0,
        "preco_promocional": 80.0,
        "desconto": 20.0,
    }


def test_modulo_listagem_enriquece_preco_pdv_sem_promocao_ativa():
    agora = datetime(2026, 5, 25, 10, 0)
    produto = SimpleNamespace(
        preco_venda=100,
        preco_promocional=120,
        promocao_inicio=agora - timedelta(days=1),
        promocao_fim=agora + timedelta(days=1),
    )

    resultado = enriquecer_preco_pdv(produto, referencia=agora)

    assert resultado.preco_venda_original == 100.0
    assert resultado.preco_venda_pdv == 100.0
    assert resultado.preco_venda_efetivo == 100.0
    assert resultado.promocao_pdv_ativa is False
    assert resultado.promocao_origem_pdv is None
    assert resultado.desconto_promocional_pdv == 0.0


def test_modulo_listagem_calcula_estoque_virtual_com_reservas_do_mesmo_tenant():
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

    with patch(
        "app.produtos.listagem.KitEstoqueService.calcular_estoque_virtual_kit",
        return_value=31,
    ) as calcular_estoque_virtual:
        resultado = enriquecer_produto_listagem(
            db,
            produto,
            tenant_id="tenant-1",
            reservas_por_produto={10: 2.0},
            incluir_detalhes_composto=False,
        )

    calcular_estoque_virtual.assert_called_once_with(
        db,
        produto.id,
        tenant_id=produto.tenant_id,
        reservas_por_produto={10: 2.0},
    )
    assert resultado.composicao_kit == []
    assert resultado.estoque_virtual == 31
    assert resultado.estoque_disponivel == 31
    assert resultado.de_parceiro is False
