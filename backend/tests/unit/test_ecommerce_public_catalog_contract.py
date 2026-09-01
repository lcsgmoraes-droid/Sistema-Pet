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


def test_catalog_brand_names_are_clean_unique_and_case_insensitive_sorted():
    assert ecommerce_public._normalize_catalog_brand_names(
        [("zMarca",), (" alpha ",), ("Beta",), ("alpha",), (None,), ()]
    ) == ["alpha", "Beta", "zMarca"]


def test_public_filters_query_does_not_order_distinct_brands_by_lower_expression():
    source = inspect.getsource(ecommerce_public.listar_filtros_produtos_publicos)

    assert "db.query(Marca.nome)" in source
    assert ".distinct()" in source
    assert ".order_by(func.lower(Marca.nome)" not in source
    assert "_normalize_catalog_brand_names(marcas)" in source


def test_public_products_route_exposes_category_filter_and_facets():
    signature = inspect.signature(ecommerce_public.listar_produtos_publicos)
    source = inspect.getsource(ecommerce_public.listar_produtos_publicos)

    assert "categoria_id" in signature.parameters
    assert "categoria_ids" in signature.parameters
    assert "Produto.categoria_id.in_(selected_category_ids)" in source
    assert '"categorias"' in source
    assert "_build_category_path_map" in source


def test_public_catalog_uses_shared_visibility_rule_that_blocks_zero_price():
    filters_source = inspect.getsource(
        ecommerce_public.listar_filtros_produtos_publicos
    )
    detail_source = inspect.getsource(ecommerce_public.obter_produto_publico_por_id)
    list_source = inspect.getsource(ecommerce_public.listar_produtos_publicos)

    assert "catalog_public_visibility_filters" in filters_source
    assert "catalog_public_visibility_filters" in detail_source
    assert "catalog_public_visibility_filters" in list_source
