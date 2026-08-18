"""Busca de produtos usada pelas tools do atendimento via WhatsApp."""

import logging
import math
import re
from typing import Any, Dict, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.whatsapp.tool_utils import _normalize_text, _only_digits
from app.whatsapp.remote_corepet_client import (
    fetch_remote_catalog,
    remote_data_enabled,
)


logger = logging.getLogger(__name__)


COMMON_PRODUCT_QUERY_TYPOS = {
    "bobdog": "bob dog",
    "bobdogue": "bob dog",
    "bob dogue": "bob dog",
    "bou dog": "bob dog",
    "specialdog": "special dog",
    "special dogue": "special dog",
    "especial dog": "special dog",
    "spesial": "special",
    "specyal": "special",
    "goud": "gold",
    "gould": "gold",
    "goold": "gold",
    "goldi": "gold",
    "goldem": "golden",
    "goden": "golden",
    "godlen": "golden",
    "canim": "canin",
    "caninn": "canin",
    "royal canine": "royal canin",
    "royal cannin": "royal canin",
    "premie": "premier",
    "premieer": "premier",
    "pedigri": "pedigree",
    "gran plus": "granplus",
    "rassao": "racao",
}


def correct_common_product_query_typos(query: str) -> str:
    """Corrige apenas erros frequentes e inequívocos de marca/linha."""
    normalized = " ".join(_normalize_text(query).split())
    if not normalized:
        return ""

    for typo, correction in COMMON_PRODUCT_QUERY_TYPOS.items():
        normalized = re.sub(
            rf"\b{re.escape(typo)}\b",
            correction,
            normalized,
        )

    # "golde" costuma significar a linha Gold quando Bob/Special Dog já foi
    # informada; sem esse contexto, costuma ser uma tentativa de "Golden".
    # A decisão vem depois dos aliases para contemplar "bou dog"/"especial dog".
    if re.search(r"\b(?:bob|special)\s*dog\b", normalized):
        normalized = re.sub(r"\bgolde\b", "gold", normalized)
    else:
        normalized = re.sub(r"\bgolde\b", "golden", normalized)
    return " ".join(normalized.split())


def _filter_remote_catalog_explicit_brand(
    result: Dict[str, Any], query: str
) -> Dict[str, Any]:
    """Evita confundir marcas quando o termo aparece apenas na descrição."""
    products = result.get("produtos")
    if not isinstance(products, list):
        return result

    normalized_query = " ".join(_normalize_text(query).split())
    brand = next(
        (
            candidate
            for candidate in ("special dog", "bob dog", "golden", "royal")
            if re.search(rf"\b{re.escape(candidate)}\b", normalized_query)
        ),
        None,
    )
    if not brand:
        return result

    required_terms = [brand]
    if brand in {"special dog", "bob dog"} and re.search(r"\bgold\b", normalized_query):
        required_terms.append("gold")

    filtered = []
    for product in products:
        if not isinstance(product, dict):
            continue
        normalized_name = " ".join(
            _normalize_text(str(product.get("nome") or "")).split()
        )
        if all(
            re.search(rf"\b{re.escape(term)}\b", normalized_name)
            for term in required_terms
        ):
            filtered.append(product)

    filtered_result = dict(result)
    filtered_result["produtos"] = filtered
    filtered_result["total"] = len(filtered)
    if not filtered:
        filtered_result["message"] = f"Nenhum produto encontrado para '{query}'"
    return filtered_result


RELAXED_GENERIC_PRODUCT_TOKENS = {
    "racao",
    "produto",
    "para",
    "cao",
    "caes",
    "gato",
    "gatos",
    "adulto",
    "adultos",
    "filhote",
    "filhotes",
    "carne",
    "frango",
    "arroz",
    "sabor",
    "e",
    "de",
    "com",
}


def matches_relaxed_product_query(produto: Any, tokens: list[str]) -> bool:
    """Aceita pequenas sobras de OCR sem perder peso/medida explícitos."""
    searchable = " ".join(
        _normalize_text(str(getattr(produto, field, "") or ""))
        for field in ("nome", "descricao_curta", "codigo", "codigo_barras")
    )
    numeric_tokens = [
        token for token in tokens if any(char.isdigit() for char in token)
    ]
    if any(token not in searchable for token in numeric_tokens):
        return False

    identity_tokens = [
        token
        for token in tokens
        if token not in RELAXED_GENERIC_PRODUCT_TOKENS
        and not any(char.isdigit() for char in token)
    ]
    if not identity_tokens:
        identity_tokens = [
            token for token in tokens if not any(char.isdigit() for char in token)
        ]
    matched_identity_tokens = sum(token in searchable for token in identity_tokens)
    minimum_matches = max(1, math.ceil(len(identity_tokens) * 0.7))
    return matched_identity_tokens >= minimum_matches


def buscar_produtos(
    db: Session,
    tenant_id: str,
    query: str,
    categoria: Optional[str] = None,
    limite: int = 5,
) -> Dict[str, Any]:
    """Busca e ordena produtos reais do catálogo da loja."""
    try:
        from app.produtos_models import Categoria, Produto

        raw_query = correct_common_product_query_typos(query)
        if not raw_query:
            return {
                "success": True,
                "produtos": [],
                "message": "Informe o produto que deseja buscar.",
            }

        if remote_data_enabled():
            remote_result = fetch_remote_catalog(
                tenant_id,
                raw_query,
                categoria=categoria,
                limite=limite,
            )
            if remote_result is not None:
                return _filter_remote_catalog_explicit_brand(remote_result, raw_query)

        limite = max(1, min(int(limite or 5), 15))
        query_norm = _normalize_text(raw_query)
        query_digits = _only_digits(raw_query)
        tokens = [token for token in query_norm.split() if token]
        like_tokens = [f"%{token}%" for token in tokens] or [f"%{query_norm}%"]

        base_query = db.query(
            Produto.id,
            Produto.nome,
            Produto.codigo,
            Produto.codigo_barras,
            Produto.preco_venda,
            Produto.estoque_atual,
            Produto.descricao_curta,
            Produto.categoria_id,
            Produto.imagem_principal,
        ).filter(
            Produto.tenant_id == tenant_id,
            Produto.situacao.is_(True),
            Produto.tipo_produto != "PAI",
        )

        if categoria:
            categoria_norm = _normalize_text(categoria)
            categoria_obj = (
                db.query(Categoria)
                .filter(
                    Categoria.tenant_id == tenant_id,
                    Categoria.nome.ilike(f"%{categoria_norm}%"),
                )
                .first()
            )
            if categoria_obj:
                base_query = base_query.filter(Produto.categoria_id == categoria_obj.id)

        filtered_query = base_query
        for token_like in like_tokens:
            filtered_query = filtered_query.filter(
                or_(
                    Produto.nome.ilike(token_like),
                    Produto.descricao_curta.ilike(token_like),
                    Produto.codigo.ilike(token_like),
                    Produto.codigo_barras.ilike(token_like),
                )
            )

        candidates = filtered_query.limit(max(limite * 8, 40)).all()

        if not candidates:
            candidates = (
                base_query.filter(
                    or_(
                        *[
                            condition
                            for token_like in like_tokens
                            for condition in (
                                Produto.nome.ilike(token_like),
                                Produto.descricao_curta.ilike(token_like),
                                Produto.codigo.ilike(token_like),
                                Produto.codigo_barras.ilike(token_like),
                            )
                        ]
                    )
                )
                .limit(max(limite * 8, 40))
                .all()
            )
            candidates = [
                product
                for product in candidates
                if matches_relaxed_product_query(product, tokens)
            ]

        if not candidates:
            return {
                "success": True,
                "produtos": [],
                "message": f"Nenhum produto encontrado para '{query}'",
            }

        def _score(produto: Any) -> float:
            score = 0.0
            nome = _normalize_text(getattr(produto, "nome", ""))
            descricao = _normalize_text(getattr(produto, "descricao_curta", ""))
            codigo = _normalize_text(getattr(produto, "codigo", ""))
            ean = _only_digits(getattr(produto, "codigo_barras", ""))
            estoque = float(getattr(produto, "estoque_atual", 0) or 0)

            if query_digits and (
                query_digits == _only_digits(codigo) or query_digits == ean
            ):
                score += 120
            elif query_digits and (
                query_digits in _only_digits(codigo) or query_digits in ean
            ):
                score += 60

            if query_norm == nome:
                score += 80
            elif query_norm and query_norm in nome:
                score += 45

            for token in tokens:
                if token in nome:
                    score += 20
                if token in descricao:
                    score += 8
                if token in codigo:
                    score += 25

            if estoque > 0:
                score += 5
            else:
                score -= 3

            return score

        ranked = sorted(candidates, key=_score, reverse=True)[:limite]
        produtos = [
            {
                "id": str(product.id),
                "nome": product.nome,
                "sku": product.codigo or "",
                "ean": product.codigo_barras or "",
                "preco": float(product.preco_venda) if product.preco_venda else 0.0,
                "estoque": float(product.estoque_atual)
                if product.estoque_atual is not None
                else 0,
                "estoque_disponivel": bool((product.estoque_atual or 0) > 0),
                "descricao": product.descricao_curta or "",
                "imagem_url": product.imagem_principal or "",
            }
            for product in ranked
        ]

        return {"success": True, "produtos": produtos, "total": len(produtos)}

    except Exception as error:
        logger.error("Erro ao buscar produtos: %s", error)
        db.rollback()
        return {"success": False, "error": str(error)}
