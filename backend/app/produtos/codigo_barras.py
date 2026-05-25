import random
from typing import Callable, Optional


def calcular_digito_verificador_ean13(codigo_12_digitos: str) -> str:
    """
    Calcula o digito verificador para codigo EAN-13.
    Algoritmo: modulo 10.
    """
    if len(codigo_12_digitos) != 12:
        raise ValueError("CÃ³digo deve ter exatamente 12 dÃ­gitos")

    soma_impar = sum(int(codigo_12_digitos[i]) for i in range(0, 12, 2))
    soma_par = sum(int(codigo_12_digitos[i]) * 3 for i in range(1, 12, 2))
    soma_total = soma_impar + soma_par
    digito = (10 - (soma_total % 10)) % 10

    return str(digito)


def gerar_codigo_barras_ean13(
    sku: str,
    randint_func: Optional[Callable[[int, int], int]] = None,
) -> str:
    """
    Gera codigo de barras EAN-13:
    789 (Brasil) + 5 digitos aleatorios + 4 ultimos digitos do SKU + checksum.
    """
    randint = randint_func or random.randint
    numeros_sku = "".join(filter(str.isdigit, sku))

    if not numeros_sku:
        numeros_sku = str(randint(1000, 9999))

    ultimos_4_sku = numeros_sku[-4:].zfill(4)
    codigo_12 = "789" + str(randint(10000, 99999)) + ultimos_4_sku
    digito_verificador = calcular_digito_verificador_ean13(codigo_12)

    return codigo_12 + digito_verificador


def limpar_codigo_barras(codigo: str) -> str:
    return codigo.replace(" ", "").replace("-", "")


def validar_codigo_barras_ean13(codigo: str) -> dict:
    codigo_limpo = limpar_codigo_barras(codigo)

    if len(codigo_limpo) != 13:
        return {
            "valido": False,
            "erro": f"CÃ³digo deve ter 13 dÃ­gitos. Fornecido: {len(codigo_limpo)} dÃ­gitos",
        }

    if not codigo_limpo.isdigit():
        return {
            "valido": False,
            "erro": "CÃ³digo deve conter apenas nÃºmeros",
        }

    codigo_12 = codigo_limpo[:12]
    digito_fornecido = codigo_limpo[12]
    digito_calculado = calcular_digito_verificador_ean13(codigo_12)

    if digito_fornecido != digito_calculado:
        return {
            "valido": False,
            "erro": f"DÃ­gito verificador invÃ¡lido. Esperado: {digito_calculado}, Fornecido: {digito_fornecido}",
        }

    return {
        "valido": True,
        "codigo_limpo": codigo_limpo,
    }
