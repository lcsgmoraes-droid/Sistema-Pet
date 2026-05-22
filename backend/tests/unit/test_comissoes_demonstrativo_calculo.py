from app.comissoes_demonstrativo_routes import montar_demonstrativo_calculo_comissao


def _linha_por_chave(demonstrativo, chave):
    return next(linha for linha in demonstrativo["linhas"] if linha["chave"] == chave)


def test_demonstrativo_lucro_mostra_custo_produto_e_comissao_final():
    demonstrativo = montar_demonstrativo_calculo_comissao(
        tipo_calculo="lucro",
        valor_bruto=99.90,
        desconto=0,
        beneficio=0,
        taxa_cartao=0,
        imposto=6.99,
        taxa_entregador=0,
        custo_operacional=0,
        receita_taxa_entrega=0,
        custo_produto=76.71,
        valor_base_calculo=16.20,
        percentual_comissao=50,
        valor_comissao=8.10,
        valor_comissao_gerada=8.10,
        percentual_aplicado=100,
    )

    chaves = [linha["chave"] for linha in demonstrativo["linhas"]]

    assert chaves[:2] == ["preco_venda", "desconto"]
    assert "custo_produto" in chaves
    assert _linha_por_chave(demonstrativo, "custo_produto")["valor"] == 76.71
    assert _linha_por_chave(demonstrativo, "base_calculo")["valor"] == 16.20
    assert _linha_por_chave(demonstrativo, "comissao_final")["valor"] == 8.10
    assert demonstrativo["formula_resumo"] == (
        "preco_venda - desconto - beneficio - taxas - impostos - entrega - custo_produto = lucro_comissionavel"
    )


def test_demonstrativo_separa_desconto_beneficio_e_entrega():
    demonstrativo = montar_demonstrativo_calculo_comissao(
        tipo_calculo="lucro",
        valor_bruto=200,
        desconto=10,
        beneficio=15,
        taxa_cartao=6,
        imposto=14,
        taxa_entregador=8,
        custo_operacional=2,
        receita_taxa_entrega=5,
        custo_produto=100,
        valor_base_calculo=50,
        percentual_comissao=50,
        valor_comissao=25,
        valor_comissao_gerada=25,
        percentual_aplicado=100,
    )

    assert _linha_por_chave(demonstrativo, "desconto")["valor"] == 10
    assert _linha_por_chave(demonstrativo, "beneficio")["valor"] == 15
    assert _linha_por_chave(demonstrativo, "receita_taxa_entrega")["operador"] == "+"
    assert _linha_por_chave(demonstrativo, "taxa_entregador")["valor"] == 8
    assert _linha_por_chave(demonstrativo, "custo_operacional_entrega")["valor"] == 2
    assert demonstrativo["lucro_conferido"] == 50
