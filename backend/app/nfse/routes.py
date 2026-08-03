from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db
from app.models import Tenant, User
from app.models_cadastros import Cliente
from app.nfse.models import NfseDocument, NfseTenantConfig
from app.nfse.providers import FocusNfeProvider, NfseProviderError
from app.nfse.providers.focus_nfe import (
    focus_token_is_configured,
    normalize_environment,
)
from app.nfse.schemas import NfseCancelRequest, NfseConfigUpdate, NfseConsultationIssue
from app.nfse.service import (
    PRESIDENTE_PRUDENTE_IBGE,
    apply_provider_response,
    build_focus_payload,
    configuration_missing_fields,
    customer_missing_fields,
    infer_customer_municipality_code,
    request_fingerprint,
    serialize_document,
)
from app.security.permissions_decorator import require_any_permission
from app.veterinario_models import ConsultaVet, ProcedimentoConsulta


router = APIRouter(prefix="/nfse", tags=["NFS-e integrada"])


def _tenant(db: Session, tenant_id: UUID) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada.")
    return tenant


def _config(
    db: Session, tenant_id: UUID, *, create: bool = False
) -> NfseTenantConfig | None:
    config = (
        db.query(NfseTenantConfig)
        .filter(NfseTenantConfig.tenant_id == tenant_id)
        .first()
    )
    if config is None and create:
        config = NfseTenantConfig(
            tenant_id=tenant_id,
            status="pending_configuration",
            provider="focus_nfe",
            environment="homologacao",
            municipality_code=PRESIDENTE_PRUDENTE_IBGE,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _config_response(tenant: Tenant, config: NfseTenantConfig) -> dict:
    token_configured = focus_token_is_configured(config.environment)
    missing = configuration_missing_fields(
        tenant, config, token_configured=token_configured
    )
    return {
        "status": config.status,
        "provider": config.provider,
        "environment": config.environment,
        "municipality": "Presidente Prudente/SP",
        "municipality_code": config.municipality_code,
        "service_list_item": config.service_list_item,
        "cnae_code": config.cnae_code,
        "iss_rate": float(config.iss_rate) if config.iss_rate is not None else None,
        "iss_withheld": config.iss_withheld,
        "operation_nature": config.operation_nature,
        "special_tax_regime": config.special_tax_regime,
        "simple_national": config.simple_national,
        "cultural_incentive": config.cultural_incentive,
        "provider_company_reference": config.provider_company_reference,
        "token_configured": token_configured,
        "ready_for_homologation": not missing and config.environment == "homologacao",
        "missing_fields": missing,
        "last_validation_error": config.last_validation_error,
        "validated_at": config.validated_at,
    }


def _ensure_emission_allowed(*, provider: str, environment: str) -> None:
    if provider != "focus_nfe":
        raise HTTPException(status_code=422, detail="Emissor de NFS-e nao suportado.")
    if environment == "producao":
        from app.config import settings

        if not settings.NFSE_PRODUCTION_ENABLED:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Emissao de NFS-e em producao esta bloqueada. "
                    "Conclua a homologacao e libere NFSE_PRODUCTION_ENABLED explicitamente."
                ),
            )


@router.get("/configuracao")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def get_configuration(
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tenant = _tenant(db, tenant_id)
    config = _config(db, tenant_id, create=True)
    return _config_response(tenant, config)


@router.put("/configuracao")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def update_configuration(
    payload: NfseConfigUpdate,
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tenant = _tenant(db, tenant_id)
    config = _config(db, tenant_id, create=True)
    updates = payload.model_dump(exclude_unset=True)

    required_values = {
        "iss_withheld": "Retencao de ISS",
        "operation_nature": "Natureza da operacao",
        "simple_national": "Opcao pelo Simples Nacional",
        "cultural_incentive": "Incentivador cultural",
    }
    for field, label in required_values.items():
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=422, detail=f"{label} nao pode ficar vazio."
            )

    if "environment" in updates:
        try:
            updates["environment"] = normalize_environment(updates["environment"])
        except NfseProviderError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if updates.get("operation_nature") not in {
        None,
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    }:
        raise HTTPException(
            status_code=422, detail="Natureza da operacao deve ficar entre 1 e 6."
        )
    if updates.get("special_tax_regime") not in {
        None,
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    }:
        raise HTTPException(
            status_code=422, detail="Regime especial deve ficar entre 1 e 6."
        )
    item = updates.get("service_list_item")
    if item and not re.fullmatch(r"\d{1,2}\.\d{2}", item.strip()):
        raise HTTPException(
            status_code=422,
            detail="Item da lista de servicos deve usar formato como 5.01.",
        )

    for key, value in updates.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(config, key, value)
    config.status = "pending_configuration"
    config.validated_at = None
    config.last_validation_error = None
    db.commit()
    db.refresh(config)
    return _config_response(tenant, config)


@router.post("/configuracao/pre-validar")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def prevalidate_configuration(
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tenant = _tenant(db, tenant_id)
    config = _config(db, tenant_id, create=True)
    missing = configuration_missing_fields(
        tenant,
        config,
        token_configured=focus_token_is_configured(config.environment),
    )
    if missing:
        config.status = "pending_configuration"
        config.last_validation_error = "Campos pendentes: " + ", ".join(missing)
        db.commit()
        raise HTTPException(
            status_code=422,
            detail={
                "message": "A configuracao fiscal ainda esta incompleta.",
                "missing_fields": missing,
            },
        )

    config.status = "validating"
    config.last_validation_error = None
    config.validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _config_response(tenant, config)


@router.post("/consultas/{consultation_id}/emitir")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def issue_consultation_nfse(
    consultation_id: int,
    payload: NfseConsultationIssue,
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    tenant = _tenant(db, tenant_id)
    config = _config(db, tenant_id)
    if config is None:
        raise HTTPException(
            status_code=422, detail="Configure a NFS-e antes de emitir."
        )
    _ensure_emission_allowed(provider=config.provider, environment=config.environment)
    missing = configuration_missing_fields(
        tenant,
        config,
        token_configured=focus_token_is_configured(config.environment),
    )
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "A configuracao fiscal esta incompleta.",
                "missing_fields": missing,
            },
        )
    if config.status not in {"validating", "active"}:
        raise HTTPException(
            status_code=422,
            detail="Execute a pre-validacao da configuracao antes de emitir.",
        )

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
            status_code=404, detail="Consulta veterinaria nao encontrada."
        )
    if consultation.status != "finalizada":
        raise HTTPException(
            status_code=422, detail="Finalize a consulta antes de emitir a NFS-e."
        )
    customer = (
        db.query(Cliente)
        .filter(Cliente.id == consultation.cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Tutor da consulta nao encontrado.")

    municipality_code = infer_customer_municipality_code(
        customer, payload.customer_municipality_code
    )
    customer_missing = customer_missing_fields(customer, municipality_code)
    if customer_missing:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Complete os dados fiscais do tutor antes de emitir.",
                "missing_fields": customer_missing,
            },
        )

    amount = payload.service_amount
    if amount is None:
        amount = (
            db.query(func.coalesce(func.sum(ProcedimentoConsulta.valor), 0))
            .filter(
                ProcedimentoConsulta.consulta_id == consultation.id,
                ProcedimentoConsulta.tenant_id == tenant_id,
                ProcedimentoConsulta.realizado.is_(True),
            )
            .scalar()
        )
        amount = Decimal(str(amount or 0))
    if amount <= 0:
        raise HTTPException(
            status_code=422,
            detail="Informe um valor de servicos maior que zero para a NFS-e.",
        )

    procedure_names = [
        row[0]
        for row in db.query(ProcedimentoConsulta.nome)
        .filter(
            ProcedimentoConsulta.consulta_id == consultation.id,
            ProcedimentoConsulta.tenant_id == tenant_id,
            ProcedimentoConsulta.realizado.is_(True),
        )
        .all()
        if row[0]
    ]
    description = payload.description or (
        "Atendimento veterinario: " + ", ".join(procedure_names)
        if procedure_names
        else f"Atendimento veterinario - consulta {consultation.id}"
    )
    reference = f"corepet-{str(tenant_id).replace('-', '')[:12]}-vet-{consultation.id}"
    provider_payload = build_focus_payload(
        tenant=tenant,
        config=config,
        customer=customer,
        customer_municipality_code=municipality_code,
        service_amount=amount,
        description=description,
        customer_email=payload.customer_email,
        issued_at=consultation.finalizado_em,
    )
    fingerprint = request_fingerprint(provider_payload)
    existing = (
        db.query(NfseDocument)
        .filter(
            NfseDocument.tenant_id == tenant_id,
            NfseDocument.reference == reference,
        )
        .first()
    )
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Ja existe uma NFS-e para esta consulta com dados diferentes. "
                    "Cancele ou regularize a nota existente antes de tentar novamente."
                ),
            )
        return serialize_document(existing)

    document = NfseDocument(
        tenant_id=tenant_id,
        reference=reference,
        request_fingerprint=fingerprint,
        provider=config.provider,
        environment=config.environment,
        status="sending",
        origin_type="veterinary_consultation",
        origin_id=str(consultation.id),
        customer_id=customer.id,
        consultation_id=consultation.id,
        issued_by_user_id=current_user.id,
        service_amount=amount,
        description=description,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(document)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Esta consulta ja possui uma solicitacao de NFS-e."
        ) from exc
    db.refresh(document)

    try:
        provider_response = FocusNfeProvider(config.environment).issue(
            reference, provider_payload
        )
        apply_provider_response(document, provider_response)
        if document.status == "sending":
            document.status = "processing"
    except NfseProviderError as exc:
        document.status = "submission_error"
        document.error_code = exc.code
        document.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    db.commit()
    db.refresh(document)
    return serialize_document(document)


def _document(db: Session, tenant_id: UUID, document_id: int) -> NfseDocument:
    document = (
        db.query(NfseDocument)
        .filter(
            NfseDocument.id == document_id,
            NfseDocument.tenant_id == tenant_id,
        )
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="NFS-e nao encontrada.")
    return document


@router.get("/consultas/{consultation_id}")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def get_consultation_document(
    consultation_id: int,
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    document = (
        db.query(NfseDocument)
        .filter(
            NfseDocument.tenant_id == tenant_id,
            NfseDocument.consultation_id == consultation_id,
        )
        .order_by(NfseDocument.created_at.desc())
        .first()
    )
    return {"document": serialize_document(document) if document else None}


@router.get("/documentos")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def list_documents(
    limit: int = 50,
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    safe_limit = min(max(limit, 1), 200)
    documents = (
        db.query(NfseDocument)
        .filter(NfseDocument.tenant_id == tenant_id)
        .order_by(NfseDocument.created_at.desc())
        .limit(safe_limit)
        .all()
    )
    return [serialize_document(document) for document in documents]


@router.post("/documentos/{document_id}/sincronizar")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def sync_document(
    document_id: int,
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    document = _document(db, tenant_id, document_id)
    try:
        response = FocusNfeProvider(document.environment).query(document.reference)
    except NfseProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    apply_provider_response(document, response)
    db.commit()
    db.refresh(document)
    return serialize_document(document)


@router.post("/documentos/{document_id}/cancelar")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def cancel_document(
    document_id: int,
    payload: NfseCancelRequest,
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    document = _document(db, tenant_id, document_id)
    config = _config(db, tenant_id)
    if config is None:
        raise HTTPException(
            status_code=422, detail="Configuracao de NFS-e nao encontrada."
        )
    _ensure_emission_allowed(
        provider=document.provider, environment=document.environment
    )
    if document.status != "authorized":
        raise HTTPException(
            status_code=422, detail="Somente NFS-e autorizada pode ser cancelada."
        )
    try:
        response = FocusNfeProvider(document.environment).cancel(
            document.reference, payload.justification.strip()
        )
    except NfseProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    apply_provider_response(document, response)
    db.commit()
    db.refresh(document)
    return serialize_document(document)
