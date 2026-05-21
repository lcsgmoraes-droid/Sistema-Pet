from pathlib import Path
import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app import estoque_saida_full_routes


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_saida_full_routes_ficam_em_router_dedicado():
    routes = {
        (route.path, ",".join(sorted(route.methods)))
        for route in estoque_saida_full_routes.router.routes
    }

    assert ("/estoque/saida-full-nf/historico", "GET") in routes
    assert ("/estoque/saida-full-nf/{numero_nf}/canal", "PUT") in routes
    assert ("/estoque/saida-full-nf/validar-estoque", "POST") in routes
    assert ("/estoque/saida-full-nf", "POST") in routes
    assert ("/estoque/saida-full-pdf/parse", "POST") in routes
    assert ("/estoque/saida-full-xml/parse", "POST") in routes


def test_estoque_routes_nao_expõe_mais_rotas_saida_full():
    source = _source("app/estoque_routes.py")

    assert '"/saida-full-nf' not in source
    assert '"/saida-full-pdf/parse"' not in source
    assert '"/saida-full-xml/parse"' not in source
    assert "class SaidaFullNFRequest" not in source
    assert "def saida_full_por_nf(" not in source


def test_main_registra_router_de_saida_full():
    main_source = _source("app/main.py")

    assert "from app.estoque_saida_full_routes import router as estoque_saida_full_router" in main_source
    assert 'app.include_router(estoque_saida_full_router, tags=["Estoque - Saida FULL"])' in main_source
