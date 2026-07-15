from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.dre_canais.agregacao import (
    _aplicar_estimativas_cmv,
    _complementar_snapshot_com_custos_reais,
)
from app.dre_canais.base import _novo_canal
from app.dre_canais.linhas import montar_linhas_dre_competencia
from app.dre_canais.routes import _montar_alertas_cmv_estimado


def test_estima_cmv_pela_proporcao_ponderada_do_mesmo_canal():
    dados = {"loja_fisica": _novo_canal()}
    bases = {
        "loja_fisica": {
            "receita_confirmada": Decimal("1000"),
            "custo_confirmado": Decimal("600"),
        }
    }
    pendencias = {
        "loja_fisica": [
            {"produto_id": 1, "valor_venda": 100},
            {"produto_id": 2, "valor_venda": 50},
        ]
    }

    _aplicar_estimativas_cmv(dados, bases, pendencias)

    assert dados["loja_fisica"]["cmv_estimado"] == Decimal("90.00")
    assert dados["loja_fisica"]["percentual_cmv_estimado"] == Decimal("60.0")
    assert dados["loja_fisica"]["origem_percentual_cmv_estimado"] == "mesmo_canal"
    assert [
        item["valor_estimado"]
        for item in dados["loja_fisica"]["itens_cmv_estimado"]
    ] == [60.0, 30.0]


def test_estima_com_base_global_quando_canal_nao_tem_amostra_confiavel():
    dados = {"shopee": _novo_canal()}
    bases = {
        "loja_fisica": {
            "receita_confirmada": Decimal("200"),
            "custo_confirmado": Decimal("100"),
        },
        "shopee": {
            "receita_confirmada": Decimal("0"),
            "custo_confirmado": Decimal("0"),
        },
    }
    pendencias = {"shopee": [{"produto_id": 3, "valor_venda": 80}]}

    _aplicar_estimativas_cmv(dados, bases, pendencias)

    assert dados["shopee"]["cmv_estimado"] == Decimal("40.00")
    assert (
        dados["shopee"]["origem_percentual_cmv_estimado"]
        == "todos_canais_periodo"
    )


def test_custo_real_cadastrado_depois_substitui_estimativa_sem_mudar_snapshot():
    produto = SimpleNamespace(preco_custo=Decimal("25"))
    item = SimpleNamespace(quantidade=Decimal("2"), produto_id=10, produto=produto)
    venda = SimpleNamespace(itens=[item])
    snapshot_original = {
        "custo_produtos": 0,
        "itens": [{"custo_total": 0, "custo_unitario": 0}],
    }

    ajustado = _complementar_snapshot_com_custos_reais(venda, snapshot_original, {})

    assert ajustado["custo_produtos"] == 50.0
    assert ajustado["itens"][0]["custo_total"] == 50.0
    assert ajustado["itens"][0]["custo_origem_complemento_dre"] == "cadastro_produto"
    assert snapshot_original["custo_produtos"] == 0
    assert snapshot_original["itens"][0]["custo_total"] == 0
    assert produto.preco_custo == Decimal("25")


def test_cmv_total_inclui_parcela_provisoria_de_forma_transparente():
    canal = _novo_canal()
    canal["receita_produtos"] = Decimal("200")
    canal["cmv"] = Decimal("60")
    canal["cmv_estimado"] = Decimal("20")
    canal["fretes_compras"] = Decimal("10")

    linhas, totais = montar_linhas_dre_competencia({"loja_fisica": canal})

    assert totais["cmv"] == pytest.approx(90.0)
    linha_estimativa = next(linha for linha in linhas if linha.campo == "cmv_estimado")
    assert linha_estimativa.valor == pytest.approx(20.0)
    assert linha_estimativa.detalhavel is True


def test_alerta_identifica_produtos_e_valores_afetados():
    canal = _novo_canal()
    canal["cmv_estimado"] = Decimal("45")
    canal["percentual_cmv_estimado"] = Decimal("60")
    canal["origem_percentual_cmv_estimado"] = "mesmo_canal"
    canal["itens_cmv_estimado"] = [
        {"produto_id": 1, "valor_venda": 50},
        {"produto_id": 1, "valor_venda": 25},
    ]

    alertas = _montar_alertas_cmv_estimado({"loja_fisica": canal})

    assert len(alertas) == 1
    assert alertas[0]["quantidade_produtos"] == 1
    assert alertas[0]["quantidade_itens"] == 2
    assert alertas[0]["valor_vendas"] == pytest.approx(75.0)
    assert alertas[0]["valor_estimado"] == pytest.approx(45.0)
    assert alertas[0]["sem_base_estimativa"] is False
