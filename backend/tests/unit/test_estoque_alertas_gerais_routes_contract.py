from pathlib import Path
import importlib
import importlib.util
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_alertas_gerais_fica_em_router_dedicado():
    spec = importlib.util.find_spec("app.estoque_alertas_gerais_routes")

    assert spec is not None

    module = importlib.import_module("app.estoque_alertas_gerais_routes")
    routes = {
        (route.path, ",".join(sorted(route.methods)))
        for route in module.router.routes
    }

    assert ("/estoque/alertas", "GET") in routes


def test_estoque_routes_nao_expoe_mais_alertas_gerais():
    source = _source("app/estoque_routes.py")

    assert '@router.get("/alertas")' not in source
    assert "def alertas_estoque(" not in source


def test_main_registra_router_de_alertas_gerais():
    main_source = _source("app/main.py")

    assert "from app.estoque_alertas_gerais_routes import router as estoque_alertas_gerais_router" in main_source
    assert 'app.include_router(estoque_alertas_gerais_router, tags=["Estoque - Alertas Gerais"])' in main_source
