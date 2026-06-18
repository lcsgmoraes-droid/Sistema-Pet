from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_whatsapp_analytics_nao_usa_datetime_utcnow():
    source = (ROOT / "app/whatsapp/analytics.py").read_text(encoding="utf-8")

    assert "datetime.utcnow()" not in source
    assert (
        "from app.whatsapp.analytics_simple import WhatsAppAnalyticsService" in source
    )
    assert "class WhatsAppAnalyticsService" not in source
