from pathlib import Path
import importlib
import importlib.util
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_movimentacoes_manuais_ficam_em_router_dedicado():
    spec = importlib.util.find_spec("app.estoque_movimentacoes_manuais_routes")

    assert spec is not None

    module = importlib.import_module("app.estoque_movimentacoes_manuais_routes")
    routes = {
        (route.path, ",".join(sorted(route.methods)))
        for route in module.router.routes
    }

    assert ("/estoque/entrada", "POST") in routes
    assert ("/estoque/saida", "POST") in routes


def test_estoque_routes_nao_expoe_mais_movimentacoes_manuais():
    source = _source("app/estoque_routes.py")

    assert '@router.post("/entrada", status_code=status.HTTP_201_CREATED)' not in source
    assert '@router.post("/saida", status_code=status.HTTP_201_CREATED)' not in source
    assert "def entrada_estoque(" not in source
    assert "def saida_estoque(" not in source
    assert "class EntradaEstoqueRequest" not in source
    assert "class SaidaEstoqueRequest" not in source


def test_main_registra_router_de_movimentacoes_manuais():
    main_source = _source("app/main.py")

    assert "from app.estoque_movimentacoes_manuais_routes import router as estoque_movimentacoes_manuais_router" in main_source
    assert 'app.include_router(estoque_movimentacoes_manuais_router, tags=["Estoque - Movimentacoes Manuais"])' in main_source
