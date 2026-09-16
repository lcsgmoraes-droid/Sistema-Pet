from types import SimpleNamespace

from app.bling_integration_fiscal import (
    _cfops_venda_por_destino,
    _valor_fiscal_produto,
)


def test_interstate_product_cfop_does_not_override_internal_company_cfop():
    company = SimpleNamespace(
        cfop_venda_interna="5102", cfop_venda_interestadual="6102"
    )

    assert _cfops_venda_por_destino("6101", company) == ("5102", "6101")


def test_internal_product_cfop_does_not_override_interstate_company_cfop():
    company = SimpleNamespace(
        cfop_venda_interna="5102", cfop_venda_interestadual="6102"
    )

    assert _cfops_venda_por_destino("5405", company) == ("5405", "6102")


def test_empty_current_fiscal_field_does_not_revive_stale_legacy_value():
    current = SimpleNamespace(cest=None)
    product = SimpleNamespace(cest="2200100")

    assert _valor_fiscal_produto(current, product, "cest", "cest") is None


def test_legacy_value_is_used_only_before_current_fiscal_record_exists():
    product = SimpleNamespace(cfop="5102")

    assert _valor_fiscal_produto(None, product, "cfop_venda", "cfop") == "5102"
