from decimal import Decimal

from app.financeiro.valor_empresa_service import calcular_cenarios, configuracao_padrao


def test_cenario_provavel_abre_composicao_do_valor():
    cenarios = calcular_cenarios(
        estoque_total=Decimal("220000"),
        estoque_lento=Decimal("54000"),
        imobilizado=Decimal("60000"),
        lucro_mensal=Decimal("1000"),
        outros_ativos=Decimal("5000"),
        dividas=Decimal("10000"),
        config=configuracao_padrao(),
    )

    provavel = next(item for item in cenarios if item["chave"] == "provavel")

    assert provavel["ajuste_estoque_lento"] == 13500
    assert provavel["estoque_negociavel"] == 206500
    assert provavel["fundo_comercio"] == 24000
    assert provavel["valor_sugerido"] == 285500


def test_fundo_de_comercio_nao_fica_negativo_quando_operacao_da_prejuizo():
    cenarios = calcular_cenarios(
        estoque_total=Decimal("10000"),
        estoque_lento=Decimal("0"),
        imobilizado=Decimal("2000"),
        lucro_mensal=Decimal("-500"),
        outros_ativos=Decimal("0"),
        dividas=Decimal("0"),
        config=configuracao_padrao(),
    )

    assert all(item["fundo_comercio"] == 0 for item in cenarios)
    assert all(item["valor_sugerido"] == 12000 for item in cenarios)


def test_desconto_incide_somente_sobre_estoque_lento():
    config = configuracao_padrao()
    config["desconto_estoque_conservador"] = Decimal("100")

    conservador = calcular_cenarios(
        estoque_total=Decimal("50000"),
        estoque_lento=Decimal("10000"),
        imobilizado=Decimal("0"),
        lucro_mensal=Decimal("0"),
        outros_ativos=Decimal("0"),
        dividas=Decimal("0"),
        config=config,
    )[0]

    assert conservador["estoque_negociavel"] == 40000
    assert conservador["valor_sugerido"] == 40000
