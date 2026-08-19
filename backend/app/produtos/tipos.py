"""Regras centrais para diferenciar produtos e servicos no catalogo."""

from __future__ import annotations

import unicodedata
from typing import Any, MutableMapping


TIPO_PRODUTO = "produto"
TIPO_SERVICO = "servico"
TIPO_PRODUTO_SERVICO = "produto_servico"


def _texto_sem_acentos(value: Any) -> str:
    texto = str(value or "").strip().lower()
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )


def normalizar_tipo_catalogo(value: Any) -> str:
    """Normaliza os tipos editaveis sem apagar tipos legados, como ``racao``."""
    original = str(value or "").strip()
    normalizado = _texto_sem_acentos(original).replace("-", "_").replace(" ", "_")

    if normalizado in {"servico", "service"}:
        return TIPO_SERVICO
    if normalizado in {"produto", "product", ""}:
        return TIPO_PRODUTO
    if normalizado in {
        "ambos",
        "produto_e_servico",
        "produto_servico",
        "servico_produto",
    }:
        return TIPO_PRODUTO_SERVICO
    return original.lower()


def tipo_controla_estoque(value: Any) -> bool:
    """Somente o tipo exclusivamente servico deixa de controlar estoque."""
    return normalizar_tipo_catalogo(value) != TIPO_SERVICO


def aplicar_regras_servico_dados(dados: MutableMapping[str, Any]) -> bool:
    """Forca invariantes de estoque quando o cadastro representa um servico."""
    tipo = normalizar_tipo_catalogo(dados.get("tipo"))
    dados["tipo"] = tipo
    if tipo != TIPO_SERVICO:
        return False

    dados.update(
        {
            "estoque_atual": 0,
            "estoque_minimo": 0,
            "estoque_maximo": 0,
            "estoque_fisico": 0,
            "estoque_ecommerce": 0,
            "controle_lote": False,
            "participa_sugestao_compra": False,
            "e_granel": False,
            "tipo_produto": "SIMPLES",
            "tipo_kit": None,
            "produto_pai_id": None,
            "is_parent": False,
            "is_sellable": True,
        }
    )
    dados.pop("e_kit_fisico", None)
    return True
