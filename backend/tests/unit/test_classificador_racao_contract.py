from app.classificador_racao import ClassificadorRacao, classificar_produto


def test_classificar_produto_detects_core_ration_attributes():
    resultado, confianca, metadata = classificar_produto(
        "Racao Super Premium Cao Adulto Pequeno Porte Frango 15kg"
    )

    assert resultado["linha_racao"] == "Super Premium"
    assert resultado["porte_animal"] == ["Pequeno"]
    assert resultado["fase_publico"] == ["Adulto"]
    assert resultado["sabor_proteina"] == "Frango"
    assert resultado["peso_embalagem"] == 15.0
    assert confianca["score"] > 0
    assert metadata["versao"] == ClassificadorRacao.VERSION
