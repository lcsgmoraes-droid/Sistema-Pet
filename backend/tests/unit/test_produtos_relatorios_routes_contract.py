EXPECTED_RELATORIO_PATHS = {
    "/relatorio/movimentacoes",
    "/relatorio/produto-vendas",
    "/relatorio/validade-proxima",
    "/relatorio/valorizacao-estoque",
}
EXPECTED_PRODUTOS_RELATORIO_PATHS = {
    f"/produtos{path}" for path in EXPECTED_RELATORIO_PATHS
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def _read_repo(path):
    from pathlib import Path

    return (Path(__file__).resolve().parents[3] / path).read_text(encoding="utf-8")


def test_produtos_relatorios_routes_ficam_em_subrouter_dedicado():
    from app.produtos.relatorios_routes import router

    assert EXPECTED_RELATORIO_PATHS.issubset(_route_paths(router))


def test_produtos_router_inclui_relatorios_sem_mudar_paths():
    from app.produtos_routes import router

    assert EXPECTED_PRODUTOS_RELATORIO_PATHS.issubset(_route_paths(router))


def test_relatorios_com_busca_de_produto_usam_regra_central_de_eans():
    validade = _read_repo("backend/app/produtos/relatorios_validade_routes.py")
    valorizacao = _read_repo("backend/app/produtos/relatorios_valorizacao_routes.py")

    assert "_produto_search_conditions(palavra)" in validade
    assert "ProdutoLote.nome_lote.ilike(busca_pattern)" in validade
    assert "_produto_search_conditions(palavra)" in valorizacao


def test_valorizacao_estoque_suporta_incluir_e_excluir_multiplos_fornecedores():
    backend_source = _read_repo("backend/app/produtos/relatorios_valorizacao_routes.py")
    frontend_source = _read_repo("frontend/src/pages/ProdutosValorizacaoEstoque.jsx")

    assert "fornecedor_ids: Optional[list[int]]" in backend_source
    assert 'fornecedor_modo: str = "incluir"' in backend_source
    assert 'fornecedor_modo_normalizado == "excluir"' in backend_source
    assert "Produto.fornecedor_id.notin_(fornecedor_ids)" in backend_source
    assert "~Produto.fornecedores_alternativos.any" in backend_source
    assert "ProdutoFornecedor.fornecedor_id.in_(fornecedor_ids)" in backend_source

    assert "fornecedor_modo" in frontend_source
    assert "fornecedor_ids" in frontend_source
    assert "fornecedores_selecionados" in frontend_source
    assert "Excluir fornecedores" in frontend_source
    assert "Tudo menos" in frontend_source
