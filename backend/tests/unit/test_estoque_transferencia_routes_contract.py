from pathlib import Path
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app import estoque_transferencia_routes


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_transferencia_simples_fica_em_router_dedicado():
    routes = {
        (route.path, ",".join(sorted(route.methods)))
        for route in estoque_transferencia_routes.router.routes
    }

    assert ("/estoque/transferencia", "POST") in routes


def test_estoque_routes_nao_expõe_mais_transferencia_simples():
    source = _source("app/estoque_routes.py")

    assert (
        '@router.post("/transferencia", status_code=status.HTTP_201_CREATED)'
        not in source
    )
    assert "def transferencia_estoque(" not in source
    assert "class TransferenciaEstoqueRequest" not in source


def test_main_registra_router_de_transferencia_simples():
    main_source = _source("app/main_routers.py")

    assert (
        "from app.estoque_transferencia_routes import router as estoque_transferencia_router"
        in main_source
    )
    assert (
        'app.include_router(estoque_transferencia_router, tags=["Estoque - Transferencia"])'
        in main_source
    )
