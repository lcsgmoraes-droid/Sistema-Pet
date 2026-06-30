from pathlib import Path

from app.clientes import financeiro_baixa_lote_routes, financeiro_routes


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _non_empty_line_count(relative_path: str) -> int:
    return sum(1 for line in _source(relative_path).splitlines() if line.strip())


def _method_paths(router):
    return {
        (getattr(route, "path", None), ",".join(sorted(getattr(route, "methods", []))))
        for route in router.routes
    }


def test_clientes_financeiro_baixa_lote_fatia_37_preserva_api_publica():
    assert (
        financeiro_routes.baixar_vendas_lote
        is financeiro_baixa_lote_routes.baixar_vendas_lote
    )
    assert ("/{cliente_id}/baixar-vendas-lote", "POST") in _method_paths(
        financeiro_routes.router
    )


def test_clientes_financeiro_routes_agrega_baixa_lote_extraida():
    source = _source("backend/app/clientes/financeiro_routes.py")
    baixa_source = _source("backend/app/clientes/financeiro_baixa_lote_routes.py")

    assert "financeiro_baixa_lote_routes" in source
    assert "router.include_router(financeiro_baixa_lote_router)" in source
    assert "MovimentacaoCaixa" not in source
    assert "FluxoCaixa" not in source
    assert "CampaignEventQueue" not in source
    assert "get_or_build_venda_rentabilidade_snapshot" not in source
    assert "MovimentacaoCaixa" in baixa_source
    assert "FluxoCaixa" in baixa_source
    assert "CampaignEventQueue" in baixa_source
    assert "get_or_build_venda_rentabilidade_snapshot" in baixa_source


def test_clientes_financeiro_fatia_37_fica_abaixo_de_700_linhas_nao_vazias():
    counts = {
        "backend/app/clientes/financeiro_routes.py": _non_empty_line_count(
            "backend/app/clientes/financeiro_routes.py"
        ),
        "backend/app/clientes/financeiro_baixa_lote_routes.py": _non_empty_line_count(
            "backend/app/clientes/financeiro_baixa_lote_routes.py"
        ),
    }

    assert counts["backend/app/clientes/financeiro_routes.py"] < 500
    assert all(lines < 700 for lines in counts.values())
