from typing import Any

from app.lgpd_models import DataSubjectRequest
from app.services.lgpd_utils import iso, json_load, utcnow
from app.whatsapp.security import DataAccessLog, DataDeletionRequest


class PrivacyAuditMixin:
    def log_data_access(
        self,
        *,
        subject_type: str,
        subject_id: str,
        access_type: str,
        resource_type: str,
        resource_id: str | None,
        accessed_by_user_id: int | None,
        ip_address: str | None,
        user_agent: str | None = None,
        justification: str | None = None,
        flush_only: bool = False,
    ) -> DataAccessLog:
        log = DataAccessLog(
            tenant_id=self.tenant_id,
            subject_type=subject_type,
            subject_id=str(subject_id),
            accessed_by_user_id=accessed_by_user_id,
            access_type=access_type,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            justification=justification,
            created_at=utcnow(),
        )
        self.db.add(log)
        self.db.flush()
        if not flush_only:
            self.db.commit()
        return log

    def _legacy_deletion_requests(
        self, subject_type: str, subject_id: str
    ) -> list[dict[str, Any]]:
        rows = (
            self.db.query(DataDeletionRequest)
            .filter(
                DataDeletionRequest.tenant_id == self.tenant_id,
                DataDeletionRequest.subject_type == subject_type,
                DataDeletionRequest.subject_id == str(subject_id),
            )
            .order_by(
                DataDeletionRequest.request_date.desc(), DataDeletionRequest.id.desc()
            )
            .limit(100)
            .all()
        )
        return [
            {
                "id": row.id,
                "status": row.status,
                "reason": row.reason,
                "request_date": iso(row.request_date),
                "processed_at": iso(row.processed_at),
                "rejection_reason": row.rejection_reason,
            }
            for row in rows
        ]

    def _linked_legacy_deletion_request(
        self, row: DataSubjectRequest
    ) -> DataDeletionRequest | None:
        payload = json_load(row.response_payload, {}) or {}
        legacy_id = payload.get("legacy_deletion_request_id")
        query = self.db.query(DataDeletionRequest).filter(
            DataDeletionRequest.tenant_id == self.tenant_id,
            DataDeletionRequest.subject_type == row.subject_type,
            DataDeletionRequest.subject_id == str(row.subject_id),
        )
        if legacy_id:
            return query.filter(DataDeletionRequest.id == legacy_id).first()

        candidates = (
            query.order_by(
                DataDeletionRequest.request_date.desc(), DataDeletionRequest.id.desc()
            )
            .limit(50)
            .all()
        )
        for candidate in candidates:
            metadata = json_load(candidate.extra_metadata, {}) or {}
            if str(metadata.get("data_subject_request_id")) == str(row.id):
                return candidate
        return None

    def _access_logs(self, subject_type: str, subject_id: str) -> list[dict[str, Any]]:
        rows = (
            self.db.query(DataAccessLog)
            .filter(
                DataAccessLog.tenant_id == self.tenant_id,
                DataAccessLog.subject_type == subject_type,
                DataAccessLog.subject_id == str(subject_id),
            )
            .order_by(DataAccessLog.created_at.desc(), DataAccessLog.id.desc())
            .limit(200)
            .all()
        )
        return [
            {
                "id": row.id,
                "access_type": row.access_type,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "accessed_by_user_id": row.accessed_by_user_id,
                "justification": row.justification,
                "created_at": iso(row.created_at),
            }
            for row in rows
        ]


__all__ = ["PrivacyAuditMixin"]
