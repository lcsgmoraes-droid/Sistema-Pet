from app.produtos.search import _only_digits, _should_use_digit_fallback


def test_digit_fallback_is_disabled_for_alphanumeric_sku():
    assert _should_use_digit_fallback("QA-PDV-B-20260515165148") is False


def test_digit_fallback_remains_enabled_for_numeric_sku_with_punctuation():
    assert _should_use_digit_fallback("023983.1") is True


def test_only_digits_normalizes_codes_for_fallback_search():
    assert _only_digits(" 023.983-1 ") == "0239831"
