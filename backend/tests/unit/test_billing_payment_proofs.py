"""Comprovante privado, revisao humana e protecao contra webhook atrasado."""

import io
from datetime import date

import pytest
from PIL import Image

import app.campaigns.models  # noqa: F401 - registra tabelas ligadas no metadata de testes
from app.services.asaas_billing_service import apply_payment_event
from app.services.billing_payment_proof_service import (
    PaymentProofError,
    review_proof,
    submit_proof,
)


def _png() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (2, 2), "white").save(stream, format="PNG")
    return stream.getvalue()


def test_comprovante_exige_revisao_e_protege_apenas_cobranca_aprovada(
    db_session, tenant_factory, user_factory
):
    tenant = tenant_factory()
    user = user_factory(tenant.id)
    tenant.billing_status = "past_due"
    tenant.billing_payment_status = "OVERDUE"
    tenant.billing_provider_payment_id = "pay_old"
    tenant.billing_next_due_date = date(2026, 9, 30)
    db_session.flush()

    proof = submit_proof(
        db_session, tenant=tenant, user_id=user.id, filename="pago.png", content=_png()
    )
    assert proof.status == "pending"
    assert tenant.billing_status == "past_due"

    with pytest.raises(PaymentProofError, match="aguardando analise"):
        submit_proof(
            db_session,
            tenant=tenant,
            user_id=user.id,
            filename="outro.png",
            content=_png(),
        )

    reviewed = review_proof(
        db_session,
        tenant=tenant,
        proof_id=proof.id,
        admin_id=1,
        approve=True,
        note="Conferido",
    )
    assert reviewed.status == "approved"
    assert reviewed.reviewer_admin_id == 1
    assert tenant.billing_status == "active"
    assert tenant.billing_payment_status == "OVERDUE"

    apply_payment_event(
        db_session,
        "PAYMENT_OVERDUE",
        {
            "id": "pay_old",
            "externalReference": tenant.id,
            "status": "OVERDUE",
            "dueDate": "2026-09-30",
        },
    )
    assert tenant.billing_status == "active"

    apply_payment_event(
        db_session,
        "PAYMENT_OVERDUE",
        {
            "id": "pay_new",
            "externalReference": tenant.id,
            "status": "OVERDUE",
            "dueDate": "2026-10-30",
        },
    )
    assert tenant.billing_status == "past_due"


def test_revisao_nao_pode_aprovar_comprovante_de_outra_empresa_ou_cobranca(
    db_session, tenant_factory, user_factory
):
    first = tenant_factory()
    first_user = user_factory(first.id)
    first.billing_provider_payment_id = "pay_first"
    first.billing_next_due_date = date(2026, 9, 30)
    db_session.flush()
    proof = submit_proof(
        db_session,
        tenant=first,
        user_id=first_user.id,
        filename="pago.png",
        content=_png(),
    )

    second = tenant_factory()
    second.billing_provider_payment_id = "pay_second"
    second.billing_next_due_date = date(2026, 9, 30)
    db_session.flush()
    with pytest.raises(PaymentProofError, match="nao encontrado"):
        review_proof(
            db_session,
            tenant=second,
            proof_id=proof.id,
            admin_id=1,
            approve=True,
            note=None,
        )

    first.billing_provider_payment_id = "pay_changed"
    with pytest.raises(PaymentProofError, match="cobranca mudou"):
        review_proof(
            db_session,
            tenant=first,
            proof_id=proof.id,
            admin_id=1,
            approve=True,
            note=None,
        )


def test_arquivo_invalido_ou_grande_e_recusado(
    db_session, tenant_factory, user_factory
):
    tenant = tenant_factory()
    user = user_factory(tenant.id)
    tenant.billing_provider_payment_id = "pay_test"
    with pytest.raises(PaymentProofError, match="Arquivo invalido"):
        submit_proof(
            db_session,
            tenant=tenant,
            user_id=user.id,
            filename="malware.pdf",
            content=b"not a pdf",
        )
    with pytest.raises(PaymentProofError, match="5 MB"):
        submit_proof(
            db_session,
            tenant=tenant,
            user_id=user.id,
            filename="gigante.png",
            content=b"x" * (5 * 1024 * 1024 + 1),
        )
