from pathlib import Path
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app import estoque_granel_routes


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_granel_routes_ficam_em_router_dedicado():
    routes = {
        (route.path, ",".join(sorted(route.methods)))
        for route in estoque_granel_routes.router.routes
    }

    assert ("/estoque/granel/produtos", "GET") in routes
    assert ("/estoque/granel/vinculos/origem/{produto_origem_id}", "GET") in routes
    assert ("/estoque/granel/alertas-preco", "GET") in routes
    assert ("/estoque/granel/vinculos", "POST") in routes
    assert ("/estoque/granel/vinculos/{vinculo_id}", "DELETE") in routes
    assert ("/estoque/granel/converter", "POST") in routes


def test_estoque_routes_nao_expõe_mais_decorators_de_granel():
    source = _source("app/estoque_routes.py")

    assert '@router.get("/granel/produtos")' not in source
    assert '@router.get("/granel/vinculos/origem/{produto_origem_id}")' not in source
    assert '@router.get("/granel/alertas-preco")' not in source
    assert (
        '@router.post("/granel/vinculos", status_code=status.HTTP_201_CREATED)'
        not in source
    )
    assert '@router.delete("/granel/vinculos/{vinculo_id}")' not in source
    assert (
        '@router.post("/granel/converter", status_code=status.HTTP_201_CREATED)'
        not in source
    )


def test_main_registra_router_de_granel():
    main_source = _source("app/main_routers.py")

    assert (
        "from app.estoque_granel_routes import router as estoque_granel_router"
        in main_source
    )
    assert (
        'app.include_router(estoque_granel_router, tags=["Estoque - Granel"])'
        in main_source
    )
