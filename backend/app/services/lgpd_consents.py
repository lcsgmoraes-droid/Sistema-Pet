from typing import Any

from app.services.lgpd_utils import PREFERENCE_TYPES, iso, utcnow
from app.whatsapp.security import DataPrivacyConsent
from app.whatsapp.tenant_context import whatsapp_tenant_context


class PrivacyConsentMixin:
    def record_consent(
        self,
        *,
        subject_type: str,
        subject_id: str,
        consent_type: str,
        consent_given: bool,
        consent_text: str,
        phone_number: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        revoke_previous: bool = True,
    ) -> DataPrivacyConsent:
        with whatsapp_tenant_context(self.tenant_id):
            now = utcnow()
            if revoke_previous:
                previous = (
                    self.db.query(DataPrivacyConsent)
                    .filter(
                        DataPrivacyConsent.tenant_id == self.tenant_id,
                        DataPrivacyConsent.subject_type == subject_type,
                        DataPrivacyConsent.subject_id == str(subject_id),
                        DataPrivacyConsent.consent_type == consent_type,
                        DataPrivacyConsent.revoked_at.is_(None),
                    )
                    .all()
                )
                for item in previous:
                    item.revoked_at = now
                    item.revoke_reason = "substituido_por_novo_registro"

            consent = DataPrivacyConsent(
                tenant_id=self.tenant_id,
                subject_type=subject_type,
                subject_id=str(subject_id),
                phone_number=phone_number,
                email=email,
                consent_type=consent_type,
                consent_given=bool(consent_given),
                consent_text=consent_text,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=now,
                updated_at=now,
            )
            self.db.add(consent)
            self.db.flush()
            return consent

    def set_customer_preferences(
        self,
        *,
        cliente,
        preferences: dict[str, bool],
        actor_user_id: int | None,
        ip_address: str | None,
        user_agent: str | None,
        source: str,
    ) -> list[DataPrivacyConsent]:
        created: list[DataPrivacyConsent] = []
        for key in PREFERENCE_TYPES:
            if key not in preferences or preferences[key] is None:
                continue
            label = "autorizado" if preferences[key] else "revogado"
            consent = self.record_consent(
                subject_type="customer",
                subject_id=str(cliente.id),
                consent_type=key,
                consent_given=bool(preferences[key]),
                consent_text=f"Preferencia {key} {label} via {source}.",
                phone_number=getattr(cliente, "telefone", None)
                or getattr(cliente, "celular", None),
                email=getattr(cliente, "email", None),
                ip_address=ip_address,
                user_agent=user_agent,
            )
            created.append(consent)

        if created:
            self.log_data_access(
                subject_type="customer",
                subject_id=str(cliente.id),
                access_type="write",
                resource_type="privacy_preferences",
                resource_id=str(cliente.id),
                accessed_by_user_id=actor_user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                justification="Atualizacao de preferencias LGPD",
            )
        return created

    def current_preferences(self, subject_type: str, subject_id: str) -> dict[str, Any]:
        result = {
            key: {
                "enabled": False,
                "defined": False,
                "updated_at": None,
                "source_text": None,
            }
            for key in PREFERENCE_TYPES
        }
        rows = (
            self.db.query(DataPrivacyConsent)
            .filter(
                DataPrivacyConsent.tenant_id == self.tenant_id,
                DataPrivacyConsent.subject_type == subject_type,
                DataPrivacyConsent.subject_id == str(subject_id),
                DataPrivacyConsent.consent_type.in_(PREFERENCE_TYPES),
            )
            .order_by(
                DataPrivacyConsent.created_at.desc(), DataPrivacyConsent.id.desc()
            )
            .all()
        )
        seen: set[str] = set()
        for row in rows:
            if row.consent_type in seen:
                continue
            seen.add(row.consent_type)
            result[row.consent_type] = {
                "enabled": bool(row.consent_given) and row.revoked_at is None,
                "defined": True,
                "updated_at": iso(row.created_at),
                "source_text": row.consent_text,
            }
        return result

    def consent_history(
        self, subject_type: str, subject_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        rows = (
            self.db.query(DataPrivacyConsent)
            .filter(
                DataPrivacyConsent.tenant_id == self.tenant_id,
                DataPrivacyConsent.subject_type == subject_type,
                DataPrivacyConsent.subject_id == str(subject_id),
            )
            .order_by(
                DataPrivacyConsent.created_at.desc(), DataPrivacyConsent.id.desc()
            )
            .limit(max(1, min(limit, 500)))
            .all()
        )
        return [self._serialize_consent(row) for row in rows]


__all__ = ["PrivacyConsentMixin"]
