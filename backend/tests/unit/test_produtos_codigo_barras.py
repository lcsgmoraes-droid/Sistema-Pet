from app.produtos.codigo_barras import (
    calcular_digito_verificador_ean13,
    gerar_codigo_barras_ean13,
    normalizar_codigo_barras,
    validar_codigo_barras_ean13,
)


def test_calcula_digito_verificador_ean13():
    assert calcular_digito_verificador_ean13("789123450123") == "3"


def test_gera_codigo_barras_ean13_com_sku_numerico_controlado():
    codigo = gerar_codigo_barras_ean13("PROD-00123", randint=lambda _a, _b: 54321)

    assert codigo == "7895432101233"
    assert validar_codigo_barras_ean13(codigo)["valido"] is True


def test_gera_codigo_barras_ean13_sem_numeros_no_sku():
    valores = iter([9876, 54321])

    codigo = gerar_codigo_barras_ean13("PRODUTO", randint=lambda _a, _b: next(valores))

    assert codigo == "7895432198769"
    assert validar_codigo_barras_ean13(codigo)["valido"] is True


def test_normaliza_codigo_barras_removendo_espacos_e_tracos():
    assert normalizar_codigo_barras("789-54321 0123-6") == "7895432101236"


def test_valida_codigo_barras_ean13_retorna_erro_amigavel():
    resultado = validar_codigo_barras_ean13("7895432101230")

    assert resultado["valido"] is False
    assert "Digito verificador invalido" in resultado["erro"]
