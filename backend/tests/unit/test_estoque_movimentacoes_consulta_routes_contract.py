from pathlib import Path
import importlib
import importlib.util
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_consulta_movimentacoes_fica_em_router_dedicado():
    spec = importlib.util.find_spec("app.estoque_movimentacoes_consulta_routes")

    assert spec is not None

    module = importlib.import_module("app.estoque_movimentacoes_consulta_routes")
    routes = {
        (route.path, ",".join(sorted(route.methods)))
        for route in module.router.routes
    }

    assert ("/estoque/movimentacoes/produto/{produto_id}", "GET") in routes
    assert ("/estoque/produto/{produto_id}/reservas-ativas", "GET") in routes


def test_estoque_routes_nao_expoe_mais_consulta_movimentacoes():
    source = _source("app/estoque_routes.py")

    assert '@router.get("/movimentacoes/produto/{produto_id}")' not in source
    assert '@router.get("/produto/{produto_id}/reservas-ativas")' not in source
    assert "def listar_movimentacoes_produto(" not in source
    assert "def listar_reservas_ativas_produto(" not in source


def test_main_registra_router_de_consulta_movimentacoes():
    main_source = _source("app/main.py")

    assert "from app.estoque_movimentacoes_consulta_routes import router as estoque_movimentacoes_consulta_router" in main_source
    assert 'app.include_router(estoque_movimentacoes_consulta_router, tags=["Estoque - Movimentacoes Consulta"])' in main_source
