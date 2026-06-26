from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_backend_relatorio_vendas_accepts_and_filters_by_sales_channel():
    routes_source = read("backend/app/relatorio_vendas_routes.py")
    builder_source = read("backend/app/relatorio_vendas_builder.py")

    assert "canal_venda: Optional[str] = Query(None)" in routes_source
    assert "_normalizar_canal_venda_relatorio" in routes_source
    assert "Venda.canal == canal_normalizado" in builder_source


def test_frontend_sends_channel_filter_to_sales_report_requests():
    controller_source = read("frontend/src/components/VendasFinanceiro.jsx")
    view_source = read("frontend/src/components/financeiro/VendasFinanceiroView.jsx")

    assert "canal_venda: filtroCanalVenda" in controller_source
    assert "filtroCanalVenda," in controller_source
    assert "setFiltroCanalVenda," in controller_source
    assert "filtroCanalVenda={filtroCanalVenda}" in view_source
    assert "setFiltroCanalVenda={setFiltroCanalVenda}" in view_source


def test_sales_report_header_exposes_channel_filter_and_clears_it():
    source = read("frontend/src/components/financeiro/VendasFinanceiroHeader.jsx")

    assert "Todos os canais" in source
    assert "filtroCanalVenda" in source
    assert 'setFiltroCanalVenda("")' in source
