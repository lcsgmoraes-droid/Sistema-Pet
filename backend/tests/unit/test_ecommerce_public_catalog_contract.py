import inspect

import pytest
from fastapi import HTTPException

from app.routes import ecommerce_public


def test_catalog_order_accepts_public_aliases():
    assert ecommerce_public._normalize_catalog_order("relevancia") == "prontos"
    assert ecommerce_public._normalize_catalog_order("nome_asc") == "nome"
    assert ecommerce_public._normalize_catalog_order("menor_preco") == "menor_preco"


def test_catalog_order_rejects_unknown_values():
    with pytest.raises(HTTPException) as exc:
        ecommerce_public._normalize_catalog_order("estoque_interno")

    assert exc.value.status_code == 400


def test_public_products_route_exposes_category_filter_and_facets():
    signature = inspect.signature(ecommerce_public.listar_produtos_publicos)
    source = inspect.getsource(ecommerce_public.listar_produtos_publicos)

    assert "categoria_id" in signature.parameters
    assert "Produto.categoria_id == categoria_id" in source
    assert '"categorias"' in source
