from pathlib import Path

from app.services import ops_tenants_common as common
from app.services import ops_tenants_read_service as read_service
from app.services import ops_tenants_service as facade


def test_ops_tenants_service_preserva_fachada_publica():
    assert facade.OpsTenantActionError is common.OpsTenantActionError
    assert facade._business_today is common._business_today
    assert facade._iso is common._iso
    assert facade._parse_date is common._parse_date
    assert facade._table_exists is common._table_exists

    assert facade.list_ops_tenants is read_service.list_ops_tenants
    assert facade._fetch_tenant_item is read_service._fetch_tenant_item
    assert facade._principal_user is read_service._principal_user
    assert facade._pilot_follow_up is read_service._pilot_follow_up
    assert facade._tenant_row_to_item is read_service._tenant_row_to_item


def test_ops_tenants_service_modulos_ficam_abaixo_de_700_linhas():
    files = [
        Path(facade.__file__),
        Path(common.__file__),
        Path(read_service.__file__),
    ]

    for path in files:
        assert len(path.read_text(encoding="utf-8").splitlines()) < 700

    facade_source = Path(facade.__file__).read_text(encoding="utf-8")
    assert "ops_tenants_read_service" in facade_source
    assert "def list_ops_tenants(" not in facade_source
    assert "def _tenant_pilot_status(" not in facade_source
