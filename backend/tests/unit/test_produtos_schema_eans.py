import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.produtos.schemas import ProdutoBase, ProdutoUpdate  # noqa: E402


def test_produto_schema_expoe_campos_ean_do_cadastro():
    for schema in (ProdutoBase, ProdutoUpdate):
        assert "codigo_barras" in schema.model_fields
        assert "gtin_ean" in schema.model_fields
        assert "gtin_ean_tributario" in schema.model_fields
        assert "codigos_barras_alternativos" in schema.model_fields
