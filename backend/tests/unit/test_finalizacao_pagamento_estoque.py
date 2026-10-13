"""O recebimento de parcelas preserva a saída realizada ao criar a venda."""

from decimal import Decimal
from unittest.mock import Mock

import pytest
from sqlalchemy.orm.attributes import set_committed_value

from app.produtos_models import Produto
from app.vendas import finalizacao
from app.vendas_models import VendaItem
from tests.unit import test_finalizacao_recebiveis_atomicidade as recebiveis

cenario = recebiveis.cenario


@pytest.mark.parametrize("valores", [(5, 10, 15), (5, 25)])
def test_receber_parcelas_e_quitar_venda_nao_baixa_estoque_novamente(
    cenario, monkeypatch, valores
):
    cenario.venda.total = Decimal("30")
    cenario.venda.subtotal = Decimal("30")
    produto = Produto(
        id=123, nome="Produto já vendido", tipo_produto="SIMPLES", estoque_atual=2
    )
    item = VendaItem(
        tenant_id=cenario.tenant,
        venda_id=cenario.venda.id,
        tipo="produto",
        produto_id=123,
        quantidade=3,
        preco_unitario=10,
        subtotal=30,
        custo_original_saida={"movimentacao_id": 321, "quantidade": "3"},
    )
    cenario.db.add(item)
    cenario.db.commit()
    set_committed_value(item, "produto", produto)
    consulta_original = cenario.db.query

    class ConsultaProduto:
        def filter(self, *args):
            return self

        def first(self):
            return produto

    def consultar(*targets, **kwargs):
        if targets == (Produto,):
            return ConsultaProduto()
        return consulta_original(*targets, **kwargs)

    monkeypatch.setattr(cenario.db, "query", consultar)
    baixar_estoque = Mock(return_value=[])
    for indice, valor in enumerate(valores):
        resultado = finalizacao.finalizar_venda(
            venda_id=cenario.venda.id,
            pagamentos=[
                {"forma_pagamento": "PIX", "forma_pagamento_id": 1, "valor": valor}
            ],
            user_id=1,
            user_nome="Teste",
            tenant_id=cenario.tenant,
            db=cenario.db,
            processar_baixa_estoque_item=baixar_estoque,
        )
        assert resultado["venda"]["status"] == (
            "finalizada" if indice == len(valores) - 1 else "baixa_parcial"
        )
        assert resultado["operacoes"]["estoque_baixado"] == []
    baixar_estoque.assert_not_called()
    assert produto.estoque_atual == 2
    assert item.custo_original_saida == {"movimentacao_id": 321, "quantidade": "3"}
