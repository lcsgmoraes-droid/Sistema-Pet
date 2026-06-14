from pathlib import Path
from uuid import UUID

from sqlalchemy.dialects import postgresql


APP_DIR = Path(__file__).resolve().parents[2] / "app"
TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")


def _source(relative_path: str) -> str:
    return (APP_DIR / relative_path).read_text(encoding="utf-8")


def _compiled_filter_for(model) -> str:
    from app.tenancy.filters import _tenant_read_filter

    return str(
        _tenant_read_filter(model, TENANT_ID).compile(
            dialect=postgresql.dialect(),
        )
    )


def test_tenant_filter_declares_partner_readable_models_and_vet_link_guard():
    source = _source("tenancy/filters.py")

    assert "PARTNER_READABLE_TENANT_TABLES" in source
    for table_name in ("clientes", "pets", "produtos"):
        assert table_name in source

    assert "VetPartnerLink" in source
    assert "VetPartnerLink.empresa_tenant_id" in source
    assert "VetPartnerLink.vet_tenant_id" in source
    assert "VetPartnerLink.ativo.is_(True)" in source
    assert "lambda cls: _tenant_read_filter(cls, tenant_id)" in source
    assert "track_base_closure_variables = False" in source
    assert "track_closure_variables=track_base_closure_variables" in source


def test_partner_readable_models_compile_with_partner_tenant_subquery():
    from app.models import Cliente, Pet
    from app.produtos_models import Produto

    for model in (Cliente, Pet, Produto):
        compiled = _compiled_filter_for(model)
        assert model.__tablename__ in compiled
        assert "vet_partner_link" in compiled
        assert "empresa_tenant_id" in compiled
        assert "vet_tenant_id" in compiled


def test_non_partner_readable_models_keep_strict_current_tenant_filter():
    from app.models import User

    compiled = _compiled_filter_for(User)

    assert "users.tenant_id" in compiled
    assert "vet_partner_link" not in compiled
