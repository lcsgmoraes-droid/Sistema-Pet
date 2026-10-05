from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app import dre_base_routes
from app.dre_calculos import calcular_cmv, calcular_custo_servicos
from app.vendas_models import Venda, VendaItem


def test_custo_mercadorias_e_servicos_sao_separados():
    produto = SimpleNamespace(
        tipo="produto", quantidade=2, produto=SimpleNamespace(preco_custo=5)
    )
    servico = SimpleNamespace(
        tipo="servico", quantidade=1, produto=SimpleNamespace(preco_custo=8)
    )
    db = MagicMock()
    consultas = {Venda: [SimpleNamespace(id=10)], VendaItem: [produto, servico]}
    db.query.side_effect = lambda modelo: _consulta_com_resultado(consultas[modelo])

    assert calcular_cmv(db, 10, 2026, "tenant-teste") == Decimal("10")
    assert calcular_custo_servicos(db, 10, 2026, "tenant-teste") == Decimal("8")


def _consulta_com_resultado(resultado):
    consulta = MagicMock()
    consulta.filter.return_value.all.return_value = resultado
    return consulta


@pytest.mark.parametrize(
    ("subtotal", "desconto_item"),
    [(210, 20), (230, 0)],
)
def test_dre_base_separa_receita_e_custo_de_servicos(
    monkeypatch, subtotal, desconto_item
):
    produto = SimpleNamespace(tipo="produto", quantidade=1, preco_unitario=100)
    servico = SimpleNamespace(
        tipo="servico", quantidade=1, preco_unitario=130, desconto_item=desconto_item
    )
    venda = SimpleNamespace(
        subtotal=subtotal,
        desconto_valor=20,
        taxa_entrega=5,
        itens=[produto, servico],
    )
    db = MagicMock()
    db.query.return_value.options.return_value.filter.return_value.all.return_value = [
        venda
    ]
    monkeypatch.setattr(dre_base_routes, "calcular_cmv", lambda *_: Decimal("45"))
    monkeypatch.setattr(
        dre_base_routes, "calcular_custo_servicos", lambda *_: Decimal("65")
    )
    monkeypatch.setattr(
        dre_base_routes,
        "obter_despesas_por_categoria",
        lambda *_: {
            "Despesas com Pessoal": Decimal("0"),
            "Despesas Administrativas": Decimal("0"),
            "Despesas com Ocupação": Decimal("0"),
            "Despesas com Vendas": Decimal("0"),
            "Outras Despesas": Decimal("0"),
        },
    )
    monkeypatch.setattr(dre_base_routes, "calcular_taxas_cartao", lambda *_: 0)

    dre = dre_base_routes.gerar_dre(
        ano=2026, mes=10, db=db, user_and_tenant=(object(), "tenant-teste")
    )

    assert dre.vendas_produtos == Decimal("100")
    assert dre.vendas_servicos == Decimal("130")
    assert dre.receita_frete == Decimal("5")
    assert dre.receita_bruta == Decimal("235")
    assert dre.receita_liquida == Decimal("215")
    assert dre.cmv == Decimal("45")
    assert dre.custo_servicos == Decimal("65")
    assert dre.lucro_bruto == Decimal("105")
