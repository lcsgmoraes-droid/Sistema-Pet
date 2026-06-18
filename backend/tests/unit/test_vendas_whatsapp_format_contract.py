from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_vendas_routes_nao_usa_datetime_utcnow():
    source = _source("app/vendas_routes.py")

    assert "datetime.utcnow()" not in source
    assert "_utcnow_naive()" in source


def test_whatsapp_analytics_nao_usa_datetime_utcnow():
    source = _source("app/whatsapp/analytics.py")

    assert "datetime.utcnow()" not in source
    assert "_utcnow_naive()" in source
