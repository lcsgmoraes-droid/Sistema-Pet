"""Normalizacoes e regras estruturais basicas de produtos."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException

from app.produtos.listagem import _as_float_optional
from app.produtos_models import Produto


def _produto_sku_value(produto: Produto) -> Optional[str]:
    return getattr(produto, "sku", None)


def _normalizar_sku_produto(sku: Optional[str]) -> str:
    sku_normalizado = str(sku or "").strip().upper()
    if not sku_normalizado:
        raise HTTPException(status_code=400, detail="SKU do produto e obrigatorio")
    return sku_normalizado


def _normalizar_filtro_ativo_produtos(
    ativo: Optional[bool],
    incluir_inativos: bool = False,
) -> Optional[bool]:
    if incluir_inativos:
        return None
    return ativo


def _normalizar_promocao_erp_payload(
    dados: dict[str, Any],
    produto_atual: Optional[Produto] = None,
) -> dict[str, Any]:
    campos_promocao = {"preco_promocional", "promocao_inicio", "promocao_fim"}

    if produto_atual is not None and not any(
        campo in dados for campo in campos_promocao
    ):
        return dados

    preco_promocional = (
        dados.get("preco_promocional")
        if "preco_promocional" in dados
        else getattr(produto_atual, "preco_promocional", None)
    )
    dados["promocao_ativa"] = bool((_as_float_optional(preco_promocional) or 0) > 0)
    return dados


def _nome_indica_granel(nome: Optional[str]) -> bool:
    return "granel" in str(nome or "").strip().lower()


def _normalizar_payload_granel(dados: dict) -> dict:
    """Aplica a regra estrutural: granel tem estoque proprio em KG e nao e item de compra."""
    if bool(dados.get("e_granel")) or _nome_indica_granel(dados.get("nome")):
        dados["e_granel"] = True
        dados["tipo_produto"] = "SIMPLES"
        dados["tipo_kit"] = None
        dados["e_kit_fisico"] = False
        dados["unidade"] = "KG"
        dados["participa_sugestao_compra"] = False
    return dados


def _aplicar_status_ativo_produto(produto: Produto, ativo: bool):
    """Mantem ativo e situacao sincronizados."""
    produto.ativo = ativo
    produto.situacao = ativo
    if not ativo:
        produto.anunciar_ecommerce = False
        produto.anunciar_app = False
    produto.updated_at = datetime.now()
