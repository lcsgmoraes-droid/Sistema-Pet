from datetime import date, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.ifood_integration_models import IfoodMarginRulesRevision, IfoodMerchantConfig
from app.integrations.ifood.management import calculate_margin
from app.routes.ifood_integration_routes import (
    IfoodCatalogConfigPayload,
    _record_margin_rules,
)
from app.tenancy.context import tenant_context


def test_old_assumptions_keep_unknown_provenance_and_contract_does_not_change_calculation():
    config = SimpleNamespace(
        commission_merchant_percent=6,
        payment_fee_percent=3,
        tax_percent=4,
        additional_unit_cost=1,
        target_margin_percent=None,
    )
    product = SimpleNamespace(preco_custo=60)
    before = calculate_margin(product, config, 100, "MERCHANT")
    assert before["rates_source"] == "unverified_store_assumptions"
    assert before["contribution"] == 26
    config.rates_reference = "Condicoes comerciais ficticias DEV"
    config.rates_valid_from = date(2026, 1, 1)
    after = calculate_margin(product, config, 100, "MERCHANT")
    assert after["rates_reference"] == config.rates_reference
    assert after["rates_valid_from"] == date(2026, 1, 1)
    assert after["contribution"] == before["contribution"]
    assert after["rates_source"] == "store_declared_contract"


def test_contract_reference_is_bounded_and_current_not_scheduled():
    assert (
        IfoodCatalogConfigPayload(rates_reference="  contrato DEV  ").rates_reference
        == "contrato DEV"
    )
    assert IfoodCatalogConfigPayload(rates_reference=" ").rates_reference is None
    with pytest.raises(ValidationError):
        IfoodCatalogConfigPayload(rates_reference="x" * 241)
    with pytest.raises(ValidationError):
        IfoodCatalogConfigPayload(rates_valid_from=date.today() + timedelta(days=1))


def test_contract_revisions_preserve_unknown_zero_actor_and_do_not_change_forecast():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[IfoodMarginRulesRevision.__table__])
    tenant = uuid4()
    config = IfoodMerchantConfig(
        tenant_id=tenant,
        merchant_id=str(uuid4()),
        commission_merchant_percent=6,
        payment_fee_percent=0,
        rates_reference="Contrato ficticio",
        rates_valid_from=date(2026, 1, 1),
    )
    with Session(engine) as db, tenant_context(tenant):
        _record_margin_rules(db, config, 7)
        db.commit()
        config.commission_merchant_percent = 8
        _record_margin_rules(db, config, 9)
        db.commit()
        revisions = (
            db.query(IfoodMarginRulesRevision)
            .order_by(IfoodMarginRulesRevision.id)
            .all()
        )
        assert len(revisions) == 2
        assert revisions[0].values["commission_merchant_percent"] == "6"
        assert revisions[1].values["commission_merchant_percent"] == "8"
        assert revisions[0].values["payment_fee_percent"] == "0"
        assert revisions[0].values["tax_percent"] is None
        assert [row.actor_id for row in revisions] == [7, 9]
        assert config.commission_merchant_percent == 8
