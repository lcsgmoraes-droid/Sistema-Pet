from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
LGPD_MODULES = [
    "app/services/lgpd_service.py",
    "app/services/lgpd_utils.py",
    "app/services/lgpd_consents.py",
    "app/services/lgpd_requests.py",
    "app/services/lgpd_customer_data.py",
    "app/services/lgpd_audit.py",
    "app/services/lgpd_serializers.py",
]


def _source(relative: str) -> str:
    return (BACKEND_ROOT / relative).read_text(encoding="utf-8")


def _line_count(relative: str) -> int:
    return len(_source(relative).splitlines())


def test_lgpd_batch_13_modules_ficam_abaixo_de_700_linhas():
    assert {relative: _line_count(relative) for relative in LGPD_MODULES} == {
        relative: count
        for relative in LGPD_MODULES
        if (count := _line_count(relative)) <= 700
    }


def test_lgpd_service_fica_fachada_publica_compativel():
    from app.services import lgpd_service
    from app.services import lgpd_utils
    from app.services.lgpd_audit import PrivacyAuditMixin
    from app.services.lgpd_consents import PrivacyConsentMixin
    from app.services.lgpd_customer_data import PrivacyCustomerDataMixin
    from app.services.lgpd_requests import PrivacySubjectRequestMixin
    from app.services.lgpd_serializers import PrivacySerializationMixin

    assert lgpd_service.PREFERENCE_TYPES is lgpd_utils.PREFERENCE_TYPES
    assert lgpd_service.DEFAULT_REQUEST_DUE_DAYS == lgpd_utils.DEFAULT_REQUEST_DUE_DAYS
    assert lgpd_service._json_dump is lgpd_utils.json_dump
    assert lgpd_service._json_load is lgpd_utils.json_load
    assert lgpd_service._iso is lgpd_utils.iso
    assert lgpd_service._num is lgpd_utils.num

    service_cls = lgpd_service.PrivacyOpsService
    for mixin in (
        PrivacyConsentMixin,
        PrivacySubjectRequestMixin,
        PrivacyCustomerDataMixin,
        PrivacyAuditMixin,
        PrivacySerializationMixin,
    ):
        assert issubclass(service_cls, mixin)


def test_lgpd_service_fachada_nao_concentra_fluxos_pesados():
    source = _source("app/services/lgpd_service.py")

    assert _line_count("app/services/lgpd_service.py") <= 120
    for method_name in (
        "record_consent",
        "create_subject_request",
        "anonymize_customer_from_request",
        "export_customer_data",
        "log_data_access",
        "_serialize_cliente",
    ):
        assert f"def {method_name}(" not in source


def test_lgpd_fluxos_ficam_nos_modulos_focados():
    assert "def record_consent(" in _source("app/services/lgpd_consents.py")
    assert "with whatsapp_tenant_context(self.tenant_id)" in _source(
        "app/services/lgpd_consents.py"
    )
    assert "def create_subject_request(" in _source("app/services/lgpd_requests.py")
    assert "def anonymize_customer_from_request(" in _source(
        "app/services/lgpd_customer_data.py"
    )
    assert "def log_data_access(" in _source("app/services/lgpd_audit.py")
    assert "def _serialize_request(" in _source("app/services/lgpd_serializers.py")
