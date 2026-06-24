import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["DEBUG"] = "false"


BACKEND_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_LOTES_ROUTES = {
    ("POST", "/{produto_id}/lotes"),
    ("GET", "/{produto_id}/lotes"),
    ("PUT", "/{produto_id}/lotes/{lote_id}"),
    ("DELETE", "/{produto_id}/lotes/{lote_id}"),
    ("POST", "/{produto_id}/entrada"),
    ("POST", "/{produto_id}/saida-fifo"),
}
EXPECTED_PRODUTOS_LOTES_ROUTES = {
    (method, f"/produtos{path}") for method, path in EXPECTED_LOTES_ROUTES
}


def _method_paths(router):
    paths = set()
    for route in router.routes:
        for method in getattr(route, "methods", set()):
            paths.add((method, getattr(route, "path", None)))
    return paths


def test_produtos_lotes_routes_ficam_em_subrouter_dedicado():
    from app.produtos.lotes_routes import router

    assert EXPECTED_LOTES_ROUTES.issubset(_method_paths(router))


def test_produtos_router_inclui_lotes_sem_mudar_paths():
    from app.produtos_routes import router

    assert EXPECTED_PRODUTOS_LOTES_ROUTES.issubset(_method_paths(router))


def test_produtos_routes_reexporta_handlers_de_lotes():
    from app import produtos_routes
    from app.produtos import lotes_routes

    for name in (
        "atualizar_lote",
        "criar_lote",
        "entrada_estoque",
        "excluir_lote",
        "listar_lotes",
        "saida_estoque_fifo",
    ):
        assert getattr(produtos_routes, name) is getattr(lotes_routes, name)


def test_produtos_routes_mantem_corte_grande_de_lotes():
    produtos_source = (BACKEND_ROOT / "app/produtos_routes.py").read_text(
        encoding="utf-8"
    )
    lotes_source = (BACKEND_ROOT / "app/produtos/lotes_routes.py").read_text(
        encoding="utf-8"
    )

    assert "def entrada_estoque(" not in produtos_source
    assert "def saida_estoque_fifo(" not in produtos_source
    assert len(produtos_source.splitlines()) < 1700
    assert len(lotes_source.splitlines()) < 550
