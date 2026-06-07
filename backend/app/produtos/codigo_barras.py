"""Helpers puros para codigo de barras de produtos."""

from __future__ import annotations

import random
from typing import Callable


def calcular_digito_verificador_ean13(codigo_12_digitos: str) -> str:
    """Calcula o digito verificador EAN-13 pelo algoritmo modulo 10."""
    if len(codigo_12_digitos) != 12:
        raise ValueError("Codigo deve ter exatamente 12 digitos")

    soma_impar = sum(int(codigo_12_digitos[i]) for i in range(0, 12, 2))
    soma_par = sum(int(codigo_12_digitos[i]) * 3 for i in range(1, 12, 2))
    return str((10 - ((soma_impar + soma_par) % 10)) % 10)


def gerar_codigo_barras_ean13(
    sku: str,
    *,
    randint: Callable[[int, int], int] = random.randint,
) -> str:
    """
    Gera EAN-13 no padrao interno:
    789 + 5 digitos aleatorios + 4 ultimos digitos numericos do SKU + checksum.
    """
    numeros_sku = "".join(filter(str.isdigit, sku))
    if not numeros_sku:
        numeros_sku = str(randint(1000, 9999))

    codigo_12 = "789" + str(randint(10000, 99999)) + numeros_sku[-4:].zfill(4)
    return codigo_12 + calcular_digito_verificador_ean13(codigo_12)


def normalizar_codigo_barras(codigo: str) -> str:
    return str(codigo or "").replace(" ", "").replace("-", "")


def validar_codigo_barras_ean13(codigo: str) -> dict:
    codigo_limpo = normalizar_codigo_barras(codigo)

    if len(codigo_limpo) != 13:
        return {
            "valido": False,
            "erro": f"Codigo deve ter 13 digitos. Fornecido: {len(codigo_limpo)} digitos",
        }

    if not codigo_limpo.isdigit():
        return {
            "valido": False,
            "erro": "Codigo deve conter apenas numeros",
        }

    codigo_12 = codigo_limpo[:12]
    digito_fornecido = codigo_limpo[12]
    digito_calculado = calcular_digito_verificador_ean13(codigo_12)

    if digito_fornecido != digito_calculado:
        return {
            "valido": False,
            "erro": (
                "Digito verificador invalido. "
                f"Esperado: {digito_calculado}, Fornecido: {digito_fornecido}"
            ),
        }

    return {
        "valido": True,
        "codigo_limpo": codigo_limpo,
    }
