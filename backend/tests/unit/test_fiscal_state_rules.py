from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.fiscal_state_rules import (
    default_company_fiscal_values,
    production_fiscal_pending,
    state_profile_payload,
)
from app.models import Tenant
from app.services.fiscal_config_service import (
    obter_ou_criar_config_fiscal_empresa_padrao,
)


@pytest.mark.parametrize(
    ("uf", "icms", "fcp"),
    [("PR", 19.5, 0.0), ("RJ", 20.0, 2.0), ("SP", 18.0, 0.0)],
)
def test_state_profile_exposes_reference_without_confirming_tax(uf, icms, fcp):
    profile = state_profile_payload(uf)
    draft = default_company_fiscal_values(uf)

    assert profile["icms_interno_referencia"] == icms
    assert profile["fcp_referencia"] == fcp
    assert float(draft["icms_aliquota_interna"]) == icms
    assert draft["configuracao_confirmada"] is False
    assert draft["aplica_difal"] is False


def test_production_requires_matching_confirmed_company_configuration():
    tenant = SimpleNamespace(uf="PR", inscricao_estadual="1234567890")
    config = SimpleNamespace(uf="SP", configuracao_confirmada=False)

    pending = production_fiscal_pending(tenant, config)

    assert any("difere" in item for item in pending)
    assert any("contabilidade" in item for item in pending)


def test_confirmed_matching_configuration_is_ready_for_production():
    tenant = SimpleNamespace(uf="RJ", inscricao_estadual="12345678")
    config = SimpleNamespace(uf="RJ", configuracao_confirmada=True)

    assert production_fiscal_pending(tenant, config) == []


def test_new_company_configuration_uses_tenant_uf_instead_of_sp(tenant_context):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine, tables=[Tenant.__table__, EmpresaConfigFiscal.__table__]
    )
    tenant_id = uuid4()
    tenant_context(tenant_id)
    with Session(engine) as db:
        db.add(
            Tenant(
                id=str(tenant_id),
                name="Tecno Agro Pet",
                name_normalized="tecno-agro-pet",
                cnpj="52028931000100",
                uf="PR",
                inscricao_estadual="1234567890",
            )
        )
        db.commit()

        config = obter_ou_criar_config_fiscal_empresa_padrao(db, tenant_id, commit=True)

        assert config.uf == "PR"
        assert float(config.icms_aliquota_interna) == 19.5
        assert config.aplica_difal is False
        assert config.configuracao_confirmada is False

        config.configuracao_confirmada = True
        tenant = db.query(Tenant).one()
        tenant.uf = "RJ"
        db.commit()

        synced = obter_ou_criar_config_fiscal_empresa_padrao(db, tenant_id, commit=True)
        assert synced.uf == "RJ"
        assert float(synced.icms_aliquota_interna) == 20.0
        assert synced.configuracao_confirmada is False
    engine.dispose()
