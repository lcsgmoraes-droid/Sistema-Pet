import pytest

from app.produtos.codigo_barras import (
    calcular_digito_verificador_ean13,
    gerar_codigo_barras_ean13,
    validar_codigo_barras_ean13,
)


def test_calcular_digito_verificador_ean13_usa_checksum_modulo_10():
    assert calcular_digito_verificador_ean13("400638133393") == "1"


def test_calcular_digito_verificador_ean13_rejeita_tamanho_invalido():
    with pytest.raises(ValueError) as exc_info:
        calcular_digito_verificador_ean13("123")

    assert str(exc_info.value) == "CÃ³digo deve ter exatamente 12 dÃ­gitos"


def test_gerar_codigo_barras_ean13_usa_prefixo_brasil_meio_e_sku():
    codigo = gerar_codigo_barras_ean13("PROD-00123", randint_func=lambda inicio, fim: 12345)

    assert codigo == "7891234501233"


def test_gerar_codigo_barras_ean13_usa_aleatorio_quando_sku_nao_tem_numero():
    valores = iter([9876, 54321])

    codigo = gerar_codigo_barras_ean13("SEM-NUMERO", randint_func=lambda inicio, fim: next(valores))

    assert codigo == "7895432198769"


def test_validar_codigo_barras_ean13_limpa_espacos_e_hifens():
    assert validar_codigo_barras_ean13("400 638-133393-1") == {
        "valido": True,
        "codigo_limpo": "4006381333931",
    }


def test_validar_codigo_barras_ean13_retorna_erro_de_tamanho():
    assert validar_codigo_barras_ean13("123") == {
        "valido": False,
        "erro": "CÃ³digo deve ter 13 dÃ­gitos. Fornecido: 3 dÃ­gitos",
    }


def test_validar_codigo_barras_ean13_retorna_erro_de_digito_verificador():
    assert validar_codigo_barras_ean13("4006381333932") == {
        "valido": False,
        "erro": "DÃ­gito verificador invÃ¡lido. Esperado: 1, Fornecido: 2",
    }
