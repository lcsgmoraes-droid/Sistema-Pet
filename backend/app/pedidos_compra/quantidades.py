"""Regras de unidade de compra para pedidos de compra."""

from __future__ import annotations

from typing import Optional


UNIDADE_COMPRA_PADRAO = "UN"
UNIDADES_COMPRA_PERMITIDAS = {"UN", "CX", "FD", "PCT", "SC"}
UNIDADES_COMPRA_COM_EMBALAGEM = UNIDADES_COMPRA_PERMITIDAS - {"UN"}


def _numero_seguro(valor: Optional[float], fallback: float = 0) -> float:
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        return fallback

    return numero if numero == numero else fallback


def _formatar_numero_curto(valor: Optional[float]) -> str:
    numero = _numero_seguro(valor)
    if numero.is_integer():
        return str(int(numero))

    texto = f"{numero:.2f}".rstrip("0").rstrip(".")
    return texto or "0"


def normalizar_unidade_compra(valor: Optional[str]) -> str:
    unidade = str(valor or UNIDADE_COMPRA_PADRAO).strip().upper()
    return unidade if unidade in UNIDADES_COMPRA_PERMITIDAS else UNIDADE_COMPRA_PADRAO


def normalizar_quantidade_por_embalagem(
    unidade_compra: Optional[str], quantidade_por_embalagem: Optional[float]
) -> float:
    unidade = normalizar_unidade_compra(unidade_compra)
    if unidade == UNIDADE_COMPRA_PADRAO:
        return 1

    quantidade = _numero_seguro(quantidade_por_embalagem, fallback=1)
    return quantidade if quantidade > 0 else 1


def calcular_quantidade_total_unidades(
    quantidade_pedida: Optional[float],
    unidade_compra: Optional[str],
    quantidade_por_embalagem: Optional[float],
) -> float:
    quantidade = _numero_seguro(quantidade_pedida)
    fator = normalizar_quantidade_por_embalagem(
        unidade_compra, quantidade_por_embalagem
    )
    return round(quantidade * fator, 4)


def formatar_quantidade_compra_documento(
    quantidade_pedida: Optional[float],
    unidade_compra: Optional[str],
    quantidade_por_embalagem: Optional[float],
) -> str:
    unidade = normalizar_unidade_compra(unidade_compra)
    quantidade = _numero_seguro(quantidade_pedida)
    fator = normalizar_quantidade_por_embalagem(unidade, quantidade_por_embalagem)
    quantidade_texto = _formatar_numero_curto(quantidade)

    if unidade == UNIDADE_COMPRA_PADRAO or fator <= 1:
        return f"{quantidade_texto} {unidade}"

    total_unidades = calcular_quantidade_total_unidades(quantidade, unidade, fator)
    return (
        f"{quantidade_texto} {unidade} ({_formatar_numero_curto(total_unidades)} unid)"
    )
