from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.models import AuditLog, Tenant, User
from app.models_cadastros import Cliente
from app.nfse_manual.models import NfseManualDocument
from app.nfse_manual.schemas import (
    NfseCancelRequest,
    NfseDraftUpdate,
    NfsePrepareRequest,
    NfseRegisterRequest,
)
from app.nfse_manual.service import (
    PRESIDENTE_PRUDENTE_PORTAL,
    attachment_path,
    build_preparation_snapshot,
    parse_nfse_xml,
    serialize_document,
    sha256_hex,
    store_attachment,
    validate_attachment,
)
from app.security.permissions_decorator import require_any_permission
from app.veterinario_models import ConsultaVet, ProcedimentoConsulta


router = APIRouter(prefix="/nfse-manual", tags=["NFS-e manual assistida"])
NFSE_PERMISSIONS = (
    "configuracoes.empresa",
    "configuracoes.editar",
    "vendas.visualizar",
)


def _tenant(db: Session, tenant_id: UUID) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return tenant


def _fiscal_config(db: Session, tenant_id: UUID, tenant: Tenant) -> EmpresaConfigFiscal:
    config = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    if config is not None:
        defaults_changed = False
        if not config.municipio_iss and tenant.cidade:
            config.municipio_iss = tenant.cidade
            defaults_changed = True
        is_prudente = (
            tenant.cidade or ""
        ).strip().lower() == "presidente prudente" and (tenant.uf or "").upper() == "SP"
        if is_prudente and not config.municipio_iss_codigo:
            config.municipio_iss_codigo = "3541406"
            defaults_changed = True
        if is_prudente and not config.nfse_portal_url:
            config.nfse_portal_url = PRESIDENTE_PRUDENTE_PORTAL
            defaults_changed = True
        if not config.nfse_natureza_operacao:
            config.nfse_natureza_operacao = "1"
            defaults_changed = True
        if defaults_changed:
            db.flush()
        return config
    is_prudente = (tenant.cidade or "").strip().lower() == "presidente prudente" and (
        tenant.uf or ""
    ).upper() == "SP"
    config = EmpresaConfigFiscal(
        tenant_id=tenant_id,
        uf=(tenant.uf or "SP").upper(),
        regime_tributario="Simples Nacional",
        contribuinte_icms=True,
        icms_aliquota_interna=18,
        icms_aliquota_interestadual=12,
        aplica_difal=True,
        cfop_venda_interna="5102",
        cfop_venda_interestadual="6102",
        cfop_compra="1102",
        herdado_do_estado=True,
        municipio_iss=tenant.cidade,
        municipio_iss_codigo="3541406" if is_prudente else None,
        iss_retido=False,
        nfse_natureza_operacao="1",
        nfse_incentivador_cultural=False,
        nfse_portal_url=(PRESIDENTE_PRUDENTE_PORTAL if is_prudente else None),
    )
    db.add(config)
    db.flush()
    return config


def _document(db: Session, tenant_id: UUID, document_id: int) -> NfseManualDocument:
    document = (
        db.query(NfseManualDocument)
        .filter(
            NfseManualDocument.id == document_id,
            NfseManualDocument.tenant_id == tenant_id,
        )
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="NFS-e não encontrada.")
    return document


def _audit(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: int,
    action: str,
    document: NfseManualDocument,
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type="nfse_manual",
            entity_id=document.id,
            details=json.dumps(details or {}, ensure_ascii=False, default=str),
        )
    )


def _duplicate_invoice(
    db: Session, tenant_id: UUID, invoice_number: str, document_id: int
) -> bool:
    return (
        db.query(NfseManualDocument.id)
        .filter(
            NfseManualDocument.tenant_id == tenant_id,
            NfseManualDocument.invoice_number == invoice_number,
            NfseManualDocument.id != document_id,
        )
        .first()
        is not None
    )


@router.post("/consultas/{consultation_id}/preparar")
@require_any_permission(NFSE_PERMISSIONS)
def prepare_consultation_document(
    consultation_id: int,
    payload: NfsePrepareRequest,
    db: Session = Depends(get_session),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    consultation = (
        db.query(ConsultaVet)
        .filter(
            ConsultaVet.id == consultation_id,
            ConsultaVet.tenant_id == tenant_id,
        )
        .first()
    )
    if consultation is None:
        raise HTTPException(
            status_code=404, detail="Consulta veterinária não encontrada."
        )
    if consultation.status != "finalizada":
        raise HTTPException(
            status_code=422, detail="Finalize a consulta antes de preparar a NFS-e."
        )
    customer = (
        db.query(Cliente)
        .filter(
            Cliente.id == consultation.cliente_id,
            Cliente.tenant_id == tenant_id,
        )
        .first()
    )
    if customer is None:
        raise HTTPException(
            status_code=404, detail="Cliente da consulta não encontrado."
        )

    procedures = (
        db.query(ProcedimentoConsulta)
        .filter(
            ProcedimentoConsulta.consulta_id == consultation.id,
            ProcedimentoConsulta.tenant_id == tenant_id,
            ProcedimentoConsulta.realizado.is_(True),
        )
        .order_by(ProcedimentoConsulta.id)
        .all()
    )
    amount = payload.service_amount
    if amount is None:
        amount = Decimal(
            str(
                db.query(func.coalesce(func.sum(ProcedimentoConsulta.valor), 0))
                .filter(
                    ProcedimentoConsulta.consulta_id == consultation.id,
                    ProcedimentoConsulta.tenant_id == tenant_id,
                    ProcedimentoConsulta.realizado.is_(True),
                )
                .scalar()
                or 0
            )
        )
    names = [item.nome.strip() for item in procedures if (item.nome or "").strip()]
    description = (payload.description or "").strip() or (
        "Atendimento veterinário: " + ", ".join(names)
        if names
        else f"Atendimento veterinário - consulta {consultation.id}"
    )
    tenant = _tenant(db, tenant_id)
    fiscal = _fiscal_config(db, tenant_id, tenant)
    snapshot = build_preparation_snapshot(
        tenant=tenant,
        customer=customer,
        fiscal=fiscal,
        consultation=consultation,
        amount=amount,
        description=description,
    )
    reference = f"corepet-{str(tenant_id).replace('-', '')[:12]}-vet-{consultation.id}"
    document = (
        db.query(NfseManualDocument)
        .filter(
            NfseManualDocument.tenant_id == tenant_id,
            NfseManualDocument.reference == reference,
        )
        .first()
    )
    if document is not None and document.status != "draft":
        return serialize_document(document)
    if document is None:
        document = NfseManualDocument(
            tenant_id=tenant_id,
            reference=reference,
            status="draft",
            origin_type="veterinary_consultation",
            origin_id=str(consultation.id),
            customer_id=customer.id,
            consultation_id=consultation.id,
            prepared_by_user_id=user.id,
            service_amount=amount,
            description=description,
            service_code=fiscal.nfse_item_lista_servico,
            iss_rate=fiscal.iss_aliquota,
            iss_withheld=bool(fiscal.iss_retido),
            preparation_snapshot=snapshot,
        )
        db.add(document)
    else:
        document.service_amount = amount
        document.description = description
        document.service_code = fiscal.nfse_item_lista_servico
        document.iss_rate = fiscal.iss_aliquota
        document.iss_withheld = bool(fiscal.iss_retido)
        document.preparation_snapshot = snapshot
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Esta consulta já possui um rascunho de NFS-e."
        ) from exc
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        action="nfse_manual_prepared",
        document=document,
        details={"consultation_id": consultation.id},
    )
    db.commit()
    db.refresh(document)
    return serialize_document(document)


@router.get("/consultas/{consultation_id}")
@require_any_permission(NFSE_PERMISSIONS)
def get_consultation_document(
    consultation_id: int,
    db: Session = Depends(get_session),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    document = (
        db.query(NfseManualDocument)
        .filter(
            NfseManualDocument.tenant_id == tenant_id,
            NfseManualDocument.consultation_id == consultation_id,
        )
        .order_by(NfseManualDocument.created_at.desc())
        .first()
    )
    return {"document": serialize_document(document) if document else None}


@router.get("/documentos")
@require_any_permission(NFSE_PERMISSIONS)
def list_documents(
    status: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_session),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    query = db.query(NfseManualDocument).filter(
        NfseManualDocument.tenant_id == tenant_id
    )
    if status:
        if status not in {"draft", "issued", "cancelled"}:
            raise HTTPException(status_code=422, detail="Situação de NFS-e inválida.")
        query = query.filter(NfseManualDocument.status == status)
    documents = (
        query.order_by(NfseManualDocument.created_at.desc())
        .limit(min(max(limit, 1), 300))
        .all()
    )
    return [serialize_document(document) for document in documents]


@router.put("/documentos/{document_id}/rascunho")
@require_any_permission(NFSE_PERMISSIONS)
def update_draft(
    document_id: int,
    payload: NfseDraftUpdate,
    db: Session = Depends(get_session),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    document = _document(db, tenant_id, document_id)
    if document.status != "draft":
        raise HTTPException(
            status_code=422, detail="Somente rascunhos podem ser alterados."
        )
    description = payload.description.strip()
    if len(description) < 3:
        raise HTTPException(
            status_code=422, detail="Descreva o serviço com pelo menos 3 caracteres."
        )
    document.service_amount = payload.service_amount
    document.description = description
    snapshot = dict(document.preparation_snapshot or {})
    snapshot["service"] = {
        **(snapshot.get("service") or {}),
        "amount": float(payload.service_amount),
        "description": document.description,
    }
    document.preparation_snapshot = snapshot
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        action="nfse_manual_draft_updated",
        document=document,
    )
    db.commit()
    db.refresh(document)
    return serialize_document(document)


@router.post("/documentos/{document_id}/registrar")
@require_any_permission(NFSE_PERMISSIONS)
def register_issued_document(
    document_id: int,
    payload: NfseRegisterRequest,
    db: Session = Depends(get_session),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    document = _document(db, tenant_id, document_id)
    if document.status == "cancelled":
        raise HTTPException(
            status_code=422, detail="A NFS-e está marcada como cancelada."
        )
    invoice_number = payload.invoice_number.strip()
    if not invoice_number:
        raise HTTPException(status_code=422, detail="Informe o número da NFS-e.")
    if _duplicate_invoice(db, tenant_id, invoice_number, document.id):
        raise HTTPException(
            status_code=409, detail="Este número de NFS-e já está registrado."
        )
    document.invoice_number = invoice_number
    document.verification_code = (payload.verification_code or "").strip() or None
    document.issued_at = payload.issued_at or datetime.now(timezone.utc)
    document.notes = (payload.notes or "").strip() or None
    document.status = "issued"
    document.registered_by_user_id = user.id
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        action="nfse_manual_registered",
        document=document,
        details={"invoice_number": invoice_number},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Este número de NFS-e já está registrado."
        ) from exc
    db.refresh(document)
    return serialize_document(document)


@router.post("/documentos/{document_id}/marcar-cancelada")
@require_any_permission(NFSE_PERMISSIONS)
def mark_cancelled(
    document_id: int,
    payload: NfseCancelRequest,
    db: Session = Depends(get_session),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    if not payload.confirm:
        raise HTTPException(
            status_code=422,
            detail="Confirme que o cancelamento já foi realizado na Prefeitura.",
        )
    document = _document(db, tenant_id, document_id)
    if document.status != "issued":
        raise HTTPException(
            status_code=422,
            detail="Somente NFS-e emitida pode ser marcada como cancelada.",
        )
    document.status = "cancelled"
    document.cancelled_at = datetime.now(timezone.utc)
    cancellation_reason = payload.reason.strip()
    if len(cancellation_reason) < 5:
        raise HTTPException(
            status_code=422, detail="Informe um motivo de cancelamento válido."
        )
    document.cancellation_reason = cancellation_reason
    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        action="nfse_manual_cancelled",
        document=document,
        details={"reason": document.cancellation_reason},
    )
    db.commit()
    db.refresh(document)
    return serialize_document(document)


@router.post("/documentos/{document_id}/anexos/{kind}")
@require_any_permission(NFSE_PERMISSIONS)
async def upload_attachment(
    document_id: int,
    kind: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    user, tenant_id = user_and_tenant
    document = _document(db, tenant_id, document_id)
    limit = 10 * 1024 * 1024 if kind == "pdf" else 5 * 1024 * 1024
    content = await file.read(limit + 1)
    validate_attachment(kind, file.filename, content)
    metadata = parse_nfse_xml(content) if kind == "xml" else None
    if metadata:
        parsed_amount = metadata.get("service_amount")
        if parsed_amount is not None and not 0 < parsed_amount <= Decimal(
            "9999999999.99"
        ):
            raise HTTPException(
                status_code=422,
                detail="O valor de serviços no XML está fora do limite permitido.",
            )
        if metadata.get("invoice_number"):
            number = metadata["invoice_number"].strip()[:80]
            if _duplicate_invoice(db, tenant_id, number, document.id):
                raise HTTPException(
                    status_code=409,
                    detail="O XML pertence a uma NFS-e já registrada.",
                )

    safe_upload_name = (file.filename or f"nfse.{kind}").replace("\\", "/")
    original_name = "".join(
        character
        for character in Path(safe_upload_name).name
        if character.isprintable()
    )[:255]
    stored_name = store_attachment(
        tenant_id=tenant_id,
        document_id=document.id,
        kind=kind,
        content=content,
    )
    setattr(document, f"{kind}_file_name", stored_name)
    setattr(document, f"{kind}_original_name", original_name)
    setattr(document, f"{kind}_sha256", sha256_hex(content))

    if metadata is not None:
        number = metadata.get("invoice_number")
        if number:
            document.invoice_number = number.strip()[:80]
            document.verification_code = (
                metadata.get("verification_code") or ""
            ).strip()[:120] or document.verification_code
            document.issued_at = (
                metadata.get("issued_at")
                or document.issued_at
                or datetime.now(timezone.utc)
            )
            parsed_amount = metadata.get("service_amount")
            if parsed_amount is not None:
                document.service_amount = parsed_amount
                snapshot = dict(document.preparation_snapshot or {})
                snapshot["service"] = {
                    **(snapshot.get("service") or {}),
                    "amount": float(parsed_amount),
                }
                document.preparation_snapshot = snapshot
            document.status = "issued"
            document.registered_by_user_id = user.id

    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        action=f"nfse_manual_{kind}_uploaded",
        document=document,
        details={"filename": original_name},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Este número de NFS-e já está registrado."
        ) from exc
    db.refresh(document)
    return serialize_document(document)


@router.get("/documentos/{document_id}/anexos/{kind}")
@require_any_permission(NFSE_PERMISSIONS)
def download_attachment(
    document_id: int,
    kind: str,
    db: Session = Depends(get_session),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    document = _document(db, tenant_id, document_id)
    if kind not in {"pdf", "xml"}:
        raise HTTPException(status_code=404, detail="Tipo de anexo inválido.")
    filename = getattr(document, f"{kind}_file_name")
    original_name = getattr(document, f"{kind}_original_name") or f"nfse.{kind}"
    path = attachment_path(
        tenant_id=tenant_id,
        document_id=document.id,
        filename=filename,
    )
    media_type = "application/pdf" if kind == "pdf" else "application/xml"
    return FileResponse(path, media_type=media_type, filename=original_name)
