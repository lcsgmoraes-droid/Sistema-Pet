from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_bling_catalog_client_can_create_product():
    source = read_text("backend/app/bling_integration_parts/catalogo.py")

    assert "def criar_produto" in source
    assert 'self._request("POST", "/produtos", data=payload)' in source


def test_bling_product_export_routes_are_registered():
    source = read_text("backend/app/bling_sync_routes.py")
    export_source = read_text("backend/app/bling_sync/exportacao_produtos_routes.py")

    assert "exportacao_produtos_bling_router" in source
    assert "router.include_router(exportacao_produtos_bling_router)" in source
    assert '@router.post("/produtos-bling/exportar")' in export_source
    assert '@router.post("/produtos-bling/exportar-lote")' in export_source


def test_frontend_exposes_single_and_batch_product_export():
    actions = read_text(
        "frontend/src/components/estoqueBling/useEstoqueBlingActions.js"
    )
    tabs = read_text("frontend/src/components/estoqueBling/EstoqueBlingTabs.jsx")
    panels = read_text("frontend/src/components/estoqueBling/EstoqueBlingPanels.jsx")

    assert '"/estoque/sync/produtos-bling/exportar"' in actions
    assert '"/estoque/sync/produtos-bling/exportar-lote"' in actions
    assert "Cadastrar no Bling" in tabs
    assert "Enviar selecionados" in panels


def test_product_list_exposes_bling_export_status_and_actions():
    schema = read_text("backend/app/produtos/schemas.py")
    routes = read_text("backend/app/produtos/listagem_routes.py")
    listagem = read_text("backend/app/produtos/listagem.py")
    page = read_text("frontend/src/pages/Produtos.jsx")
    columns = read_text("frontend/src/components/produtos/produtosColumns.jsx")
    header = read_text("frontend/src/components/produtos/ProdutosHeaderActions.jsx")
    hook = read_text("frontend/src/hooks/useProdutosListagem.js")

    assert "bling_produto_id" in schema
    assert "incluir_bling_sync: bool = False" in routes
    assert "joinedload(Produto.bling_sync)" in listagem
    assert "filtrosLimpos.incluir_bling_sync = true" in hook
    assert "exportarProdutoBling" in page
    assert "exportarProdutosBlingLote" in page
    assert 'key: "bling"' in columns
    assert "Sem Bling" in columns
    assert "Enviar ao Bling" in header


def test_product_list_counts_parent_variations_in_batch():
    listagem = read_text("backend/app/produtos/listagem.py")

    assert "def _mapa_total_variacoes_por_pai" in listagem
    assert "def _mapa_variacoes_por_pai" in listagem
    assert ".group_by(Produto.produto_pai_id)" in listagem
    assert "total_variacoes_por_pai = _mapa_total_variacoes_por_pai" in listagem
    assert "variacoes_por_pai = (" in listagem
