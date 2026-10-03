import pytest

from app.produtos.search import (
    _only_digits,
    _produto_search_scale_code_conditions,
    _scale_code_variants,
    _should_use_digit_fallback,
)


def test_digit_fallback_is_disabled_for_alphanumeric_sku():
    assert _should_use_digit_fallback("QA-PDV-B-20260515165148") is False


def test_digit_fallback_remains_enabled_for_numeric_sku_with_punctuation():
    assert _should_use_digit_fallback("023983.1") is True


def test_only_digits_normalizes_codes_for_fallback_search():
    assert _only_digits(" 023.983-1 ") == "0239831"


def test_scale_code_search_preserves_exact_sku_with_leading_zeros():
    assert _scale_code_variants("000150") == ("000150", "00150", "0150", "150")
    assert _scale_code_variants("000151") == ("000151", "00151", "0151", "151")
    assert _scale_code_variants("002024") == ("002024", "02024", "2024")
    assert _scale_code_variants("000000")[-1] == "0"

    sql = str(
        _produto_search_scale_code_conditions("000150").compile(
            compile_kwargs={"literal_binds": True}
        )
    )
    assert "'0150'" in sql
    assert "'150'" in sql
    assert "'15'" not in sql


def test_scale_code_search_rejects_invalid_code():
    with pytest.raises(ValueError):
        _scale_code_variants("00150")
