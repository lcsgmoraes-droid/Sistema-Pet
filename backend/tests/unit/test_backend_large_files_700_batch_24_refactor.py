import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.campaigns import statement_service as facade
from app.campaigns.statement_service_parts import (
    builder,
    cashback,
    common,
    coupons,
    loyalty,
    ranking,
)


def test_campaign_statement_service_preserva_reexports_legados():
    assert facade.build_campaign_customer_statement is (
        builder.build_campaign_customer_statement
    )

    assert facade._enum_value is common._enum_value
    assert facade._money is common._money
    assert facade._iso is common._iso
    assert facade._start_of_day is common._start_of_day
    assert facade._end_of_day is common._end_of_day
    assert facade._date_in_range is common._date_in_range
    assert facade._coupon_value is common._coupon_value
    assert facade._coupon_value_label is common._coupon_value_label
    assert facade._consumed_stamps_from_meta is common._consumed_stamps_from_meta
    assert facade._append_event is common._append_event
    assert facade._sort_weight is common._sort_weight
    assert facade._campaign_fields is common._campaign_fields
    assert facade._parse_datetime is common._parse_datetime

    assert facade._add_loyalty_stamp_events is loyalty._add_loyalty_stamp_events
    assert facade._add_loyalty_execution_events is loyalty._add_loyalty_execution_events
    assert facade._load_coupon_redemptions_by_coupon is (
        coupons._load_coupon_redemptions_by_coupon
    )
    assert facade._add_coupon_events is coupons._add_coupon_events
    assert facade._add_cashback_events is cashback._add_cashback_events
    assert facade._current_cashback_balance is cashback._current_cashback_balance
    assert facade._add_ranking_events is ranking._add_ranking_events
    assert facade._enrich_sales is ranking._enrich_sales
    assert facade._apply_running_balances is ranking._apply_running_balances


def test_campaign_statement_service_fachada_e_modulos_abaixo_de_700_linhas():
    files = [
        Path(facade.__file__),
        Path(builder.__file__),
        Path(common.__file__),
        Path(loyalty.__file__),
        Path(coupons.__file__),
        Path(cashback.__file__),
        Path(ranking.__file__),
    ]

    for path in files:
        assert len(path.read_text(encoding="utf-8").splitlines()) < 700

    facade_source = Path(facade.__file__).read_text(encoding="utf-8")
    assert "def build_campaign_customer_statement(" not in facade_source
    assert "def _add_coupon_events(" not in facade_source
    assert "def _add_cashback_events(" not in facade_source
    assert "statement_service_parts" in facade_source
