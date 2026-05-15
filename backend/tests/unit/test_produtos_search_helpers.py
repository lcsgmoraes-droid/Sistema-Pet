from app.produtos_routes import _should_use_digit_fallback


def test_digit_fallback_is_disabled_for_alphanumeric_sku():
    assert _should_use_digit_fallback("QA-PDV-B-20260515165148") is False


def test_digit_fallback_remains_enabled_for_numeric_sku_with_punctuation():
    assert _should_use_digit_fallback("023983.1") is True
