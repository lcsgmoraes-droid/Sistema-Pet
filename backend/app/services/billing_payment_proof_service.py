"""Envio privado e revisao humana de comprovantes de cobranca."""

from __future__ import annotations

import hashlib
import io
from datetime import datetime, timezone
from uuid import UUID

from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session, defer

from app.billing_models import BillingOffer, BillingPaymentProof
from app.models import Tenant
from app.services.billing_offer_service import _sync_offer_modules
from app.tenancy.context import tenant_context


MAX_PROOF_BYTES = 5 * 1024 * 1024


class PaymentProofError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _invoice_matches(proof: BillingPaymentProof, tenant: Tenant) -> bool:
    payment_id = str(tenant.billing_provider_payment_id or "")
    if payment_id:
        return proof.provider_payment_id == payment_id
    return (
        proof.provider_payment_id is None
        and proof.due_date is not None
        and proof.due_date == tenant.billing_next_due_date
    )


def approved_proof_for_invoice(
    db: Session, tenant: Tenant
) -> BillingPaymentProof | None:
    with tenant_context(tenant.id):
        query = (
            db.query(BillingPaymentProof)
            .options(defer(BillingPaymentProof.content))
            .filter(
                BillingPaymentProof.tenant_id == UUID(str(tenant.id)),
                BillingPaymentProof.status == "approved",
            )
        )
        if tenant.billing_provider_payment_id:
            query = query.filter(
                BillingPaymentProof.provider_payment_id
                == tenant.billing_provider_payment_id
            )
        elif tenant.billing_next_due_date:
            query = query.filter(
                BillingPaymentProof.provider_payment_id.is_(None),
                BillingPaymentProof.due_date == tenant.billing_next_due_date,
            )
        else:
            return None
        return query.order_by(BillingPaymentProof.reviewed_at.desc()).first()


def proof_to_public(proof: BillingPaymentProof) -> dict:
    return {
        "id": proof.id,
        "status": proof.status,
        "filename": proof.filename,
        "due_date": proof.due_date.isoformat() if proof.due_date else None,
        "submitted_at": proof.submitted_at.isoformat() if proof.submitted_at else None,
        "reviewed_at": proof.reviewed_at.isoformat() if proof.reviewed_at else None,
        "review_note": proof.review_note,
    }


def _validated_type(content: bytes) -> str:
    if content.startswith(b"%PDF-") and b"%%EOF" in content[-2048:]:
        return "application/pdf"
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in {"JPEG", "PNG"}:
                raise PaymentProofError("Envie um PDF, JPG ou PNG.", 422)
            image.verify()
            return "image/jpeg" if image.format == "JPEG" else "image/png"
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise PaymentProofError(
            "Arquivo invalido. Envie um PDF, JPG ou PNG.", 422
        ) from exc


def submit_proof(
    db: Session, *, tenant: Tenant, user_id: int, filename: str, content: bytes
) -> BillingPaymentProof:
    if str(tenant.billing_payment_status or "").upper() in {
        "CONFIRMED",
        "RECEIVED",
        "RECEIVED_IN_CASH",
    }:
        raise PaymentProofError(
            "O pagamento ja foi confirmado para esta cobranca.", 409
        )
    if not tenant.billing_provider_payment_id and not tenant.billing_next_due_date:
        raise PaymentProofError(
            "Ainda nao ha uma cobranca identificada para esta empresa.", 409
        )
    if not content or len(content) > MAX_PROOF_BYTES:
        raise PaymentProofError("O arquivo deve ter ate 5 MB.", 413)
    content_type = _validated_type(content)
    with tenant_context(tenant.id):
        pending = (
            db.query(BillingPaymentProof)
            .options(defer(BillingPaymentProof.content))
            .filter(
                BillingPaymentProof.tenant_id == UUID(str(tenant.id)),
                BillingPaymentProof.status == "pending",
            )
            .all()
        )
        if any(_invoice_matches(proof, tenant) for proof in pending):
            raise PaymentProofError(
                "Ja existe um comprovante aguardando analise para esta cobranca.", 409
            )
        proof = BillingPaymentProof(
            tenant_id=UUID(str(tenant.id)),
            submitted_by_user_id=user_id,
            provider_payment_id=tenant.billing_provider_payment_id,
            due_date=tenant.billing_next_due_date,
            filename=(
                filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip() or "comprovante"
            )[:180],
            content_type=content_type,
            content_sha256=hashlib.sha256(content).hexdigest(),
            content=content,
            status="pending",
        )
        db.add(proof)
        db.flush()
        return proof


def review_proof(
    db: Session,
    *,
    tenant: Tenant,
    proof_id: int,
    admin_id: int,
    approve: bool,
    note: str | None,
) -> BillingPaymentProof:
    with tenant_context(tenant.id):
        proof = (
            db.query(BillingPaymentProof)
            .filter(
                BillingPaymentProof.id == proof_id,
                BillingPaymentProof.tenant_id == UUID(str(tenant.id)),
            )
            .with_for_update()
            .first()
        )
        if proof is None:
            raise PaymentProofError("Comprovante nao encontrado.", 404)
        if proof.status != "pending":
            raise PaymentProofError("Este comprovante ja foi analisado.", 409)
        if approve and not _invoice_matches(proof, tenant):
            raise PaymentProofError(
                "A cobranca mudou. Solicite um novo comprovante.", 409
            )
        proof.status = "approved" if approve else "rejected"
        proof.reviewer_admin_id = admin_id
        proof.review_note = (note or "").strip() or None
        proof.reviewed_at = datetime.now(timezone.utc)
        if approve:
            tenant.billing_status = "active"
            offer = (
                db.query(BillingOffer)
                .filter(
                    BillingOffer.tenant_reference == str(tenant.id),
                    BillingOffer.revoked.is_(False),
                    BillingOffer.status.in_(["active", "past_due", "blocked"]),
                )
                .order_by(BillingOffer.accepted_at.desc())
                .first()
            )
            if offer is not None and (
                not offer.provider_payment_id
                or offer.provider_payment_id == tenant.billing_provider_payment_id
                or offer.provider_subscription_id
                == tenant.billing_provider_subscription_id
            ):
                offer.status = "active"
                _sync_offer_modules(db, offer=offer, tenant=tenant, active=True)
        db.flush()
        return proof
