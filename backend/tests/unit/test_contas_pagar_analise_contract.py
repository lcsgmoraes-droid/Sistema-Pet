from pathlib import Path

from app import contas_pagar_routes


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_contas_pagar_registra_rota_de_analise_de_abertos():
    from app.financeiro import contas_pagar_analise_routes

    paths = {route.path for route in contas_pagar_routes.router.routes}

    assert "/contas-pagar/analise-abertos" in paths
    assert (
        contas_pagar_routes.analisar_contas_pagar_abertas
        is contas_pagar_analise_routes.analisar_contas_pagar_abertas
    )


def test_analise_contas_pagar_tem_filtros_de_exclusao_e_totalizadores():
    source = read_repo("backend/app/financeiro/contas_pagar_analise_routes.py")

    assert "fornecedor_ids: Optional[List[int]]" in source
    assert 'fornecedor_modo: str = Query("incluir"' in source
    assert 'fornecedor_modo_normalizado == "excluir"' in source
    assert "ContaPagar.fornecedor_id.notin_(fornecedor_ids)" in source
    assert 'ContaPagar.status.notin_(["pago", "cancelado"])' in source
    assert "ContaPagar.valor_final - ContaPagar.valor_pago" in source
    assert "vencido" in source
    assert "hoje" in source
    assert "amanha" in source
    assert "proximos_12_meses" in source
    assert "por_fornecedor" in source
    assert "por_tipo_despesa" in source
    assert "agenda_mensal" in source
