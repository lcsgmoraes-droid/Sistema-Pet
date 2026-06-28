from sqlalchemy.orm import Session

from app.services.lgpd_audit import PrivacyAuditMixin
from app.services.lgpd_consents import PrivacyConsentMixin
from app.services.lgpd_customer_data import PrivacyCustomerDataMixin
from app.services.lgpd_requests import PrivacySubjectRequestMixin
from app.services.lgpd_serializers import PrivacySerializationMixin
from app.services.lgpd_utils import (
    COMPLETED_DELETION_SCRUB_NOTE,
    DEFAULT_REQUEST_DUE_DAYS,
    PREFERENCE_TYPES,
    iso as _iso,
    json_default as _json_default,
    json_dump as _json_dump,
    json_load as _json_load,
    num as _num,
    utcnow,
)


class PrivacyOpsService(
    PrivacyConsentMixin,
    PrivacySubjectRequestMixin,
    PrivacyCustomerDataMixin,
    PrivacyAuditMixin,
    PrivacySerializationMixin,
):
    """General LGPD operations used by ERP, ecommerce and app clients."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = str(tenant_id)


__all__ = [
    "COMPLETED_DELETION_SCRUB_NOTE",
    "DEFAULT_REQUEST_DUE_DAYS",
    "PREFERENCE_TYPES",
    "PrivacyOpsService",
    "_iso",
    "_json_default",
    "_json_dump",
    "_json_load",
    "_num",
    "utcnow",
]
