from typing import Any, Optional

from fastapi import HTTPException


def as_float_optional(valor: Any) -> Optional[float]:
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def produto_sku_value(produto) -> Optional[str]:
    return getattr(produto, "sku", None)


def normalizar_sku_produto(sku: Optional[str]) -> str:
    sku_normalizado = str(sku or "").strip().upper()
    if not sku_normalizado:
        raise HTTPException(status_code=400, detail="SKU do produto e obrigatorio")
    return sku_normalizado


def normalizar_promocao_erp_payload(
    dados: dict[str, Any],
    produto_atual=None,
) -> dict[str, Any]:
    campos_promocao = {"preco_promocional", "promocao_inicio", "promocao_fim"}

    if produto_atual is not None and not any(campo in dados for campo in campos_promocao):
        return dados

    preco_promocional = (
        dados.get("preco_promocional")
        if "preco_promocional" in dados
        else getattr(produto_atual, "preco_promocional", None)
    )
    dados["promocao_ativa"] = bool((as_float_optional(preco_promocional) or 0) > 0)
    return dados


def nome_indica_granel(nome: Optional[str]) -> bool:
    return "granel" in str(nome or "").strip().lower()


def normalizar_payload_granel(dados: dict) -> dict:
    if bool(dados.get("e_granel")) or nome_indica_granel(dados.get("nome")):
        dados["e_granel"] = True
        dados["tipo_produto"] = "SIMPLES"
        dados["tipo_kit"] = None
        dados["e_kit_fisico"] = False
        dados["unidade"] = "KG"
        dados["participa_sugestao_compra"] = False
    return dados
