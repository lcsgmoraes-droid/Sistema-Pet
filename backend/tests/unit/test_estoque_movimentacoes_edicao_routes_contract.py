from pathlib import Path
import importlib
import importlib.util
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_edicao_movimentacoes_fica_em_router_dedicado():
    spec = importlib.util.find_spec("app.estoque_movimentacoes_edicao_routes")

    assert spec is not None

    module = importlib.import_module("app.estoque_movimentacoes_edicao_routes")
    routes = {
        (route.path, ",".join(sorted(route.methods))) for route in module.router.routes
    }

    assert ("/estoque/movimentacoes/{movimentacao_id}", "DELETE") in routes
    assert ("/estoque/movimentacoes/{movimentacao_id}", "PATCH") in routes


def test_estoque_routes_nao_expoe_mais_edicao_movimentacoes():
    source = _source("app/estoque_routes.py")

    assert '@router.delete("/movimentacoes/{movimentacao_id}")' not in source
    assert '@router.patch("/movimentacoes/{movimentacao_id}")' not in source
    assert "def excluir_movimentacao(" not in source
    assert "def editar_movimentacao(" not in source
    assert "class UpdateMovimentacaoRequest" not in source


def test_main_registra_router_de_edicao_movimentacoes():
    main_source = _source("app/main.py")
    normalized_source = " ".join(main_source.split())

    assert "from app.estoque_movimentacoes_edicao_routes import (" in main_source
    assert "router as estoque_movimentacoes_edicao_router" in main_source
    assert "app.include_router(" in main_source
    assert (
        'estoque_movimentacoes_edicao_router, tags=["Estoque - Movimentacoes Edicao"]'
        in normalized_source
    )
