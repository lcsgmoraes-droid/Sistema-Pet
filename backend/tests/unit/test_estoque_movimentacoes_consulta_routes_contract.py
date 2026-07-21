from pathlib import Path
import importlib
import importlib.util
import os

import pytest

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
        (route.path, ",".join(sorted(route.methods))) for route in module.router.routes
    }

    assert ("/estoque/movimentacoes/produto/{produto_id}", "GET") in routes
    assert (
        "/estoque/movimentacoes/produto/{produto_id}/vendas-por-canal",
        "GET",
    ) in routes
    assert ("/estoque/produto/{produto_id}/reservas-ativas", "GET") in routes


def test_resumo_de_vendas_por_canal_preserva_destaques_e_totais():
    module = importlib.import_module("app.estoque_movimentacoes_consulta_routes")

    resultado = module._agrupar_vendas_por_canal(
        [
            {"canal": "shopee", "quantidade": 2, "preco_venda_unitario": 10},
            {"canal": "amazon", "quantidade": 4, "preco_venda_unitario": 5},
        ]
    )

    assert [item["canal"] for item in resultado[:2]] == ["amazon", "shopee"]
    assert resultado[0]["valor"] == 20
    assert resultado[0]["pct"] == pytest.approx(100 * 4 / 6)
    assert {"loja_fisica", "mercado_livre"}.issubset(
        {item["canal"] for item in resultado}
    )


def test_estoque_routes_nao_expoe_mais_consulta_movimentacoes():
    source = _source("app/estoque_routes.py")

    assert '@router.get("/movimentacoes/produto/{produto_id}")' not in source
    assert '@router.get("/produto/{produto_id}/reservas-ativas")' not in source
    assert "def listar_movimentacoes_produto(" not in source
    assert "def listar_reservas_ativas_produto(" not in source


def test_main_registra_router_de_consulta_movimentacoes():
    main_source = _source("app/main_routers.py")

    assert "from app.estoque_movimentacoes_consulta_routes import (" in main_source
    assert "router as estoque_movimentacoes_consulta_router" in main_source
    assert "app.include_router(" in main_source
    assert "estoque_movimentacoes_consulta_router" in main_source
    assert 'tags=["Estoque - Movimentacoes Consulta"]' in main_source
