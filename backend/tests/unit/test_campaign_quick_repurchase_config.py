from app.campaigns.handlers.quick_repurchase import _quick_repurchase_cooldown_days
from app.campaigns.routes import _build_manual_coupon_meta


def test_quick_repurchase_cooldown_days_uses_configured_value():
    assert _quick_repurchase_cooldown_days({"cooldown_days": 15}) == 15


def test_quick_repurchase_cooldown_days_keeps_existing_default():
    assert _quick_repurchase_cooldown_days({}) == 60


def test_quick_repurchase_cooldown_days_allows_zero_to_disable_interval():
    assert _quick_repurchase_cooldown_days({"cooldown_days": 0}) == 0


def test_build_manual_coupon_meta_exposes_reason_and_rules():
    meta = _build_manual_coupon_meta(
        motivo="Aniversario 7 anos da loja",
        descricao="Bexiga premiada",
    )

    assert meta["criado_por"] == "manual"
    assert meta["motivo"] == "Aniversario 7 anos da loja"
    assert meta["campaign_name"] == "Aniversario 7 anos da loja"
    assert meta["descricao"] == "Bexiga premiada"
    assert "gestor" in meta["regras_resumo"].lower()
