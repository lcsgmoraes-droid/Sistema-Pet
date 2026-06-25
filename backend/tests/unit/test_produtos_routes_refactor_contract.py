from pathlib import Path

from app import produtos_routes
from app.produtos import (
    atualizacao_lote_routes,
    cadastro_routes,
    codigo_sku_routes,
    estado_routes,
    listagem_routes,
    variacoes_fusao_routes,
)


ROOT = Path(__file__).resolve().parents[2]


def _method_paths(router):
    paths = set()
    for route in router.routes:
        for method in getattr(route, "methods", set()):
            paths.add((method, getattr(route, "path", None)))
    return paths


def test_produtos_routes_preserva_paths_publicos_extraidos():
    paths = _method_paths(produtos_routes.router)

    assert ("POST", "/produtos/gerar-codigo-barras") in paths
    assert ("GET", "/produtos/validar-codigo-barras/{codigo}") in paths
    assert ("POST", "/produtos/gerar-sku") in paths
    assert ("POST", "/produtos/") in paths
    assert ("GET", "/produtos/vendaveis") in paths
    assert ("GET", "/produtos/") in paths
    assert ("GET", "/produtos/{produto_id}/variacoes") in paths
    assert ("GET", "/produtos/{produto_id}/variacoes/excluidas") in paths
    assert ("PATCH", "/produtos/{produto_id}/restaurar") in paths
    assert ("POST", "/produtos/fusao/preview") in paths
    assert ("POST", "/produtos/fusao/executar") in paths
    assert ("DELETE", "/produtos/{produto_id}/permanente") in paths
    assert ("GET", "/produtos/{produto_id}") in paths
    assert ("PUT", "/produtos/{produto_id}") in paths
    assert ("PATCH", "/produtos/atualizar-lote") in paths
    assert ("PATCH", "/produtos/{produto_id}") in paths
    assert ("DELETE", "/produtos/{produto_id}") in paths
    assert ("PATCH", "/produtos/{produto_id}/ativo") in paths


def test_produtos_routes_reexporta_handlers_extraidos():
    assert produtos_routes.gerar_codigo_barras is codigo_sku_routes.gerar_codigo_barras
    assert (
        produtos_routes.validar_codigo_barras is codigo_sku_routes.validar_codigo_barras
    )
    assert produtos_routes.gerar_sku is codigo_sku_routes.gerar_sku
    assert produtos_routes.criar_produto is cadastro_routes.criar_produto
    assert produtos_routes.obter_produto is cadastro_routes.obter_produto
    assert produtos_routes.atualizar_produto is cadastro_routes.atualizar_produto
    assert produtos_routes.listar_produtos is listagem_routes.listar_produtos
    assert (
        produtos_routes.listar_produtos_vendaveis
        is listagem_routes.listar_produtos_vendaveis
    )
    assert (
        produtos_routes.listar_variacoes_produto
        is variacoes_fusao_routes.listar_variacoes_produto
    )
    assert (
        produtos_routes.preview_fusao_produtos
        is variacoes_fusao_routes.preview_fusao_produtos
    )
    assert (
        produtos_routes.atualizar_produtos_lote
        is atualizacao_lote_routes.atualizar_produtos_lote
    )
    assert produtos_routes.deletar_produto is estado_routes.deletar_produto
    assert (
        produtos_routes.atualizar_status_ativo_produto
        is estado_routes.atualizar_status_ativo_produto
    )


def test_produtos_routes_stays_below_large_file_threshold_after_extraction():
    extracted_sources = [
        ROOT / "app" / "produtos_routes.py",
        ROOT / "app" / "produtos" / "codigo_sku_routes.py",
        ROOT / "app" / "produtos" / "cadastro_routes.py",
        ROOT / "app" / "produtos" / "listagem_routes.py",
        ROOT / "app" / "produtos" / "variacoes_fusao_routes.py",
        ROOT / "app" / "produtos" / "atualizacao_lote_routes.py",
        ROOT / "app" / "produtos" / "estado_routes.py",
    ]

    assert len(extracted_sources[0].read_text(encoding="utf-8").splitlines()) < 220
    for source in extracted_sources[1:]:
        assert len(source.read_text(encoding="utf-8").splitlines()) < 700
