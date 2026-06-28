from datetime import timedelta
from typing import Any

from app.lgpd_models import DataSubjectRequest
from app.services.lgpd_utils import DEFAULT_REQUEST_DUE_DAYS, json_dump, utcnow
from app.whatsapp.security import DataDeletionRequest


class PrivacySubjectRequestMixin:
    def create_subject_request(
        self,
        *,
        subject_type: str,
        subject_id: str,
        request_type: str,
        details: str | None,
        requester_name: str | None,
        requester_email: str | None,
        requester_phone: str | None,
        channel: str,
        payload: dict[str, Any] | None,
        created_by_user_id: int | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> DataSubjectRequest:
        now = utcnow()
        subject_request = DataSubjectRequest(
            tenant_id=self.tenant_id,
            subject_type=subject_type,
            subject_id=str(subject_id),
            request_type=request_type,
            status="pending",
            requester_name=requester_name,
            requester_email=requester_email,
            requester_phone=requester_phone,
            channel=channel,
            details=details,
            request_payload=json_dump(payload),
            created_by_user_id=created_by_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            due_at=now + timedelta(days=DEFAULT_REQUEST_DUE_DAYS),
            created_at=now,
            updated_at=now,
        )
        self.db.add(subject_request)
        self.db.flush()

        if request_type == "deletion":
            legacy = DataDeletionRequest(
                tenant_id=self.tenant_id,
                subject_type=subject_type,
                subject_id=str(subject_id),
                request_date=now,
                reason=details,
                status="pending",
                contact_phone=requester_phone,
                contact_email=requester_email,
                extra_metadata=json_dump(
                    {"data_subject_request_id": subject_request.id}
                ),
            )
            self.db.add(legacy)
            self.db.flush()
            subject_request.response_payload = json_dump(
                {"legacy_deletion_request_id": legacy.id}
            )

        self.log_data_access(
            subject_type=subject_type,
            subject_id=str(subject_id),
            access_type="write",
            resource_type="data_subject_request",
            resource_id=str(subject_request.id),
            accessed_by_user_id=created_by_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            justification=f"Solicitacao LGPD criada: {request_type}",
            flush_only=True,
        )
        return subject_request

    def list_subject_requests(
        self,
        *,
        status: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = self.db.query(DataSubjectRequest).filter(
            DataSubjectRequest.tenant_id == self.tenant_id
        )
        if status:
            query = query.filter(DataSubjectRequest.status == status)
        if subject_type:
            query = query.filter(DataSubjectRequest.subject_type == subject_type)
        if subject_id:
            query = query.filter(DataSubjectRequest.subject_id == str(subject_id))
        rows = (
            query.order_by(
                DataSubjectRequest.created_at.desc(), DataSubjectRequest.id.desc()
            )
            .limit(max(1, min(limit, 500)))
            .all()
        )
        return [self._serialize_request(row) for row in rows]

    def process_subject_request(
        self,
        *,
        request_id: int,
        status: str,
        processed_by_user_id: int,
        resolution_notes: str | None = None,
        response_payload: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> DataSubjectRequest:
        allowed = {
            "pending",
            "in_review",
            "waiting_customer",
            "completed",
            "rejected",
            "cancelled",
        }
        if status not in allowed:
            raise ValueError("Status LGPD invalido")

        row = (
            self.db.query(DataSubjectRequest)
            .filter(
                DataSubjectRequest.tenant_id == self.tenant_id,
                DataSubjectRequest.id == request_id,
            )
            .first()
        )
        if not row:
            raise ValueError("Solicitacao LGPD nao encontrada")

        now = utcnow()
        row.status = status
        row.processed_by_user_id = processed_by_user_id
        row.processed_at = (
            now
            if status in {"completed", "rejected", "cancelled"}
            else row.processed_at
        )
        row.updated_at = now
        row.resolution_notes = resolution_notes
        if response_payload is not None:
            row.response_payload = json_dump(response_payload)

        self.log_data_access(
            subject_type=row.subject_type,
            subject_id=row.subject_id,
            access_type="write",
            resource_type="data_subject_request",
            resource_id=str(row.id),
            accessed_by_user_id=processed_by_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            justification=f"Solicitacao LGPD atualizada para {status}",
            flush_only=True,
        )
        return row


__all__ = ["PrivacySubjectRequestMixin"]
