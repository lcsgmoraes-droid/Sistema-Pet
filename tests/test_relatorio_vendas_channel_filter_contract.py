from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_backend_relatorio_vendas_accepts_and_filters_by_sales_channel():
    source = read("backend/app/relatorio_vendas_routes.py")

    assert "canal_venda: Optional[str] = Query(None)" in source
    assert "_normalizar_canal_venda_relatorio" in source
    assert "Venda.canal == canal_normalizado" in source


def test_frontend_sends_channel_filter_to_sales_report_requests():
    source = read("frontend/src/components/VendasFinanceiro.jsx")

    assert "canal_venda: filtroCanalVenda" in source
    assert "filtroCanalVenda," in source
    assert "setFiltroCanalVenda={setFiltroCanalVenda}" in source


def test_sales_report_header_exposes_channel_filter_and_clears_it():
    source = read("frontend/src/components/financeiro/VendasFinanceiroHeader.jsx")

    assert "Todos os canais" in source
    assert "filtroCanalVenda" in source
    assert 'setFiltroCanalVenda("")' in source
