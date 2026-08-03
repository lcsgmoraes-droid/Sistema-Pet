from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.models import Tenant, User
from app.models_cadastros import Cliente
from app.nfse.models import NfseDocument, NfseTenantConfig
from app.nfse.providers import (
    FocusNfeCompanyProvider,
    FocusNfeProvider,
    NfseProviderError,
)
from app.nfse.providers.focus_nfe import (
    focus_master_token,
    focus_master_token_is_configured,
    focus_token,
    focus_token_is_configured,
    normalize_environment,
)
from app.nfse.schemas import (
    NfseCancelRequest,
    NfseConfigUpdate,
    NfseConsultationIssue,
    NfseFocusCredentialsUpdate,
    NfseFocusOnboardingRequest,
    NfseMunicipalCredentialsUpdate,
)
from app.nfse.secrets import (
    NfseSecretConfigurationError,
    decrypt_nfse_secret,
    encrypt_nfse_secret,
    nfse_secret_is_configured,
)
from app.nfse.service import (
    PRESIDENTE_PRUDENTE_IBGE,
    apply_provider_response,
    build_focus_company_payload,
    build_focus_payload,
    configuration_missing_fields,
    customer_missing_fields,
    infer_customer_municipality_code,
    request_fingerprint,
    serialize_document,
    validate_certificate_for_cnpj,
)
from app.security.permissions_decorator import require_any_permission
from app.services.sefaz_tenant_config_service import SefazTenantConfigService
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
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _fiscal_config(
    db: Session, tenant_id: UUID, tenant: Tenant, *, create: bool = False
) -> EmpresaConfigFiscal | None:
    fiscal = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    if fiscal is None and create:
        fiscal = EmpresaConfigFiscal(
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
            municipio_iss_codigo=(
                PRESIDENTE_PRUDENTE_IBGE
                if (tenant.cidade or "").strip().lower() == "presidente prudente"
                and (tenant.uf or "").upper() == "SP"
                else None
            ),
            iss_retido=False,
            nfse_natureza_operacao="1",
            nfse_incentivador_cultural=False,
        )
        db.add(fiscal)
        db.commit()
        db.refresh(fiscal)
    return fiscal


def _certificate_bundle(tenant_id: UUID, tenant: Tenant) -> dict:
    sefaz = SefazTenantConfigService.merged_config(tenant_id, tenant)
    valid, message = validate_certificate_for_cnpj(
        sefaz.get("cert_path"), sefaz.get("cert_password"), tenant.cnpj
    )
    return {
        "configured": bool(sefaz.get("cert_path") and sefaz.get("cert_password")),
        "valid": valid,
        "message": message,
        "path": sefaz.get("cert_path") or "",
        "password": sefaz.get("cert_password") or "",
    }


def _config_response(
    tenant: Tenant,
    fiscal: EmpresaConfigFiscal,
    config: NfseTenantConfig,
    *,
    certificate: dict,
) -> dict:
    homologation_token_configured = nfse_secret_is_configured(
        config.focus_homologation_token_encrypted
    ) or focus_token_is_configured("homologacao")
    production_token_configured = nfse_secret_is_configured(
        config.focus_production_token_encrypted
    ) or focus_token_is_configured("producao")
    token_configured = (
        production_token_configured
        if config.environment == "producao"
        else homologation_token_configured
    )
    master_token_configured = (
        nfse_secret_is_configured(config.focus_master_token_encrypted)
        or focus_master_token_is_configured()
    )
    missing = configuration_missing_fields(
        tenant, fiscal, config, token_configured=token_configured
    )
    municipal_credentials_configured = nfse_secret_is_configured(
        config.municipal_login_encrypted
    ) and nfse_secret_is_configured(config.municipal_password_encrypted)
    return {
        "status": config.status,
        "provider": config.provider,
        "environment": config.environment,
        "municipality": "Presidente Prudente/SP",
        "municipality_code": fiscal.municipio_iss_codigo,
        "service_list_item": fiscal.nfse_item_lista_servico,
        "cnae_code": fiscal.cnae_principal,
        "iss_rate": float(fiscal.iss_aliquota)
        if fiscal.iss_aliquota is not None
        else None,
        "iss_withheld": bool(fiscal.iss_retido),
        "operation_nature": fiscal.nfse_natureza_operacao or "1",
        "special_tax_regime": fiscal.nfse_regime_especial_tributacao,
        "simple_national": bool(fiscal.simples_ativo)
        or "simples" in (fiscal.regime_tributario or "").lower(),
        "tax_regime": fiscal.regime_tributario,
        "cultural_incentive": bool(fiscal.nfse_incentivador_cultural),
        "provider_company_reference": config.provider_company_reference,
        "token_configured": token_configured,
        "homologation_token_configured": homologation_token_configured,
        "production_token_configured": production_token_configured,
        "master_token_configured": master_token_configured,
        "municipal_credentials_configured": municipal_credentials_configured,
        "onboarding_method": config.onboarding_method,
        "provider_onboarding_completed": bool(config.provider_onboarding_completed_at),
        "certificate": {
            "configured": certificate["configured"],
            "valid": certificate["valid"],
            "message": certificate["message"],
            "shared_with_provider": bool(config.certificate_shared_at),
        },
        "focus_signup_url": "https://focusnfe.com.br/cadastro/",
        "ready_for_homologation": not missing and config.environment == "homologacao",
        "missing_fields": missing,
        "last_validation_error": config.last_validation_error,
        "validated_at": config.validated_at,
    }


def _response_for(
    db: Session, tenant_id: UUID, tenant: Tenant, config: NfseTenantConfig
) -> dict:
    fiscal = _fiscal_config(db, tenant_id, tenant, create=True)
    certificate = _certificate_bundle(tenant_id, tenant)
    return _config_response(tenant, fiscal, config, certificate=certificate)


def _municipal_credentials(config: NfseTenantConfig) -> tuple[str, str]:
    try:
        return (
            decrypt_nfse_secret(config.municipal_login_encrypted),
            decrypt_nfse_secret(config.municipal_password_encrypted),
        )
    except NfseSecretConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _focus_environment_token(config: NfseTenantConfig, environment: str) -> str:
    encrypted = (
        config.focus_production_token_encrypted
        if environment == "producao"
        else config.focus_homologation_token_encrypted
    )
    try:
        return decrypt_nfse_secret(encrypted) or focus_token(environment)
    except NfseSecretConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _focus_master_token(config: NfseTenantConfig) -> str:
    try:
        return (
            decrypt_nfse_secret(config.focus_master_token_encrypted)
            or focus_master_token()
        )
    except NfseSecretConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _onboarding_missing_fields(
    tenant: Tenant,
    fiscal: EmpresaConfigFiscal,
    certificate: dict,
    municipal_login: str,
    municipal_password: str,
    master_token_configured: bool,
) -> list[str]:
    missing: list[str] = []
    for value, label in (
        (tenant.cnpj, "CNPJ"),
        (tenant.razao_social, "razao social"),
        (tenant.inscricao_municipal, "inscricao municipal"),
        (tenant.endereco, "logradouro"),
        (tenant.numero, "numero do endereco"),
        (tenant.bairro, "bairro"),
        (tenant.cidade, "cidade"),
        (tenant.uf, "UF"),
        (tenant.cep, "CEP"),
        (fiscal.regime_tributario, "regime tributario"),
    ):
        if not (str(value or "").strip()):
            missing.append(label)
    if not certificate["valid"]:
        missing.append("certificado A1 valido e pertencente ao CNPJ")
    if not municipal_login:
        missing.append("login da prefeitura")
    if not municipal_password:
        missing.append("senha da prefeitura")
    if not master_token_configured:
        missing.append("token master da conta Focus NFe")
    return missing


def _company_reference(payload: dict) -> str | None:
    nested = payload.get("empresa")
    if not isinstance(nested, dict):
        nested = {}
    value = (
        payload.get("id")
        or payload.get("empresa_id")
        or payload.get("uuid")
        or nested.get("id")
        or nested.get("empresa_id")
        or nested.get("uuid")
    )
    return str(value) if value not in (None, "") else None


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
    return _response_for(db, tenant_id, tenant, config)


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

    if "environment" in updates:
        try:
            updates["environment"] = normalize_environment(updates["environment"])
        except NfseProviderError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    for key, value in updates.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(config, key, value)
    config.status = "pending_configuration"
    config.validated_at = None
    config.last_validation_error = None
    db.commit()
    db.refresh(config)
    return _response_for(db, tenant_id, tenant, config)


@router.put("/credenciais-municipais")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def update_municipal_credentials(
    payload: NfseMunicipalCredentialsUpdate,
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tenant = _tenant(db, tenant_id)
    config = _config(db, tenant_id, create=True)
    try:
        if payload.clear:
            config.municipal_login_encrypted = None
            config.municipal_password_encrypted = None
        else:
            if payload.login is not None:
                config.municipal_login_encrypted = encrypt_nfse_secret(payload.login)
            if payload.password is not None:
                config.municipal_password_encrypted = encrypt_nfse_secret(
                    payload.password
                )
            if not nfse_secret_is_configured(
                config.municipal_login_encrypted
            ) or not nfse_secret_is_configured(config.municipal_password_encrypted):
                raise HTTPException(
                    status_code=422,
                    detail="Informe login e senha da prefeitura para salvar.",
                )
    except NfseSecretConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    config.status = "pending_configuration"
    config.validated_at = None
    db.commit()
    db.refresh(config)
    return _response_for(db, tenant_id, tenant, config)


@router.put("/credenciais-focus")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def update_focus_credentials(
    payload: NfseFocusCredentialsUpdate,
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tenant = _tenant(db, tenant_id)
    config = _config(db, tenant_id, create=True)
    try:
        if payload.clear:
            config.focus_master_token_encrypted = None
            config.focus_homologation_token_encrypted = None
            config.focus_production_token_encrypted = None
        else:
            if payload.master_token is not None:
                config.focus_master_token_encrypted = encrypt_nfse_secret(
                    payload.master_token
                )
            if payload.homologation_token is not None:
                config.focus_homologation_token_encrypted = encrypt_nfse_secret(
                    payload.homologation_token
                )
            if payload.production_token is not None:
                config.focus_production_token_encrypted = encrypt_nfse_secret(
                    payload.production_token
                )
    except NfseSecretConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    config.status = "pending_configuration"
    config.validated_at = None
    db.commit()
    db.refresh(config)
    return _response_for(db, tenant_id, tenant, config)


@router.post("/vinculacao-focus")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def link_focus_company(
    payload: NfseFocusOnboardingRequest,
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    if not payload.confirm:
        raise HTTPException(
            status_code=422,
            detail="Confirme a opcao escolhida antes de vincular a empresa.",
        )
    tenant = _tenant(db, tenant_id)
    config = _config(db, tenant_id, create=True)
    fiscal = _fiscal_config(db, tenant_id, tenant, create=True)
    config.onboarding_method = payload.mode

    if payload.mode == "manual":
        if payload.manual_setup_completed:
            config.provider_onboarding_completed_at = datetime.now(timezone.utc)
        config.status = "pending_configuration"
        config.validated_at = None
        db.commit()
        db.refresh(config)
        return _response_for(db, tenant_id, tenant, config)

    certificate = _certificate_bundle(tenant_id, tenant)
    municipal_login, municipal_password = _municipal_credentials(config)
    master_token = _focus_master_token(config)
    missing = _onboarding_missing_fields(
        tenant,
        fiscal,
        certificate,
        municipal_login,
        municipal_password,
        bool(master_token),
    )
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Ainda faltam dados para compartilhar o certificado.",
                "missing_fields": missing,
            },
        )

    provider_payload = build_focus_company_payload(
        tenant=tenant,
        fiscal=fiscal,
        certificate_path=certificate["path"],
        certificate_password=certificate["password"],
        municipal_login=municipal_login,
        municipal_password=municipal_password,
    )
    provider = FocusNfeCompanyProvider(token=master_token)
    try:
        if config.provider_company_reference:
            provider.update(
                config.provider_company_reference, provider_payload, dry_run=True
            )
            response = provider.update(
                config.provider_company_reference, provider_payload
            )
        else:
            provider.create(provider_payload, dry_run=True)
            response = provider.create(provider_payload)
    except NfseProviderError as exc:
        config.last_validation_error = str(exc)
        db.commit()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    config.provider_company_reference = (
        _company_reference(response) or config.provider_company_reference
    )
    now = datetime.now(timezone.utc)
    config.certificate_shared_at = now
    config.certificate_shared_by_user_id = current_user.id
    config.provider_onboarding_completed_at = now
    config.status = "pending_configuration"
    config.validated_at = None
    config.last_validation_error = None
    db.commit()
    db.refresh(config)
    return _response_for(db, tenant_id, tenant, config)


@router.post("/configuracao/pre-validar")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def prevalidate_configuration(
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    tenant = _tenant(db, tenant_id)
    config = _config(db, tenant_id, create=True)
    fiscal = _fiscal_config(db, tenant_id, tenant, create=True)
    missing = configuration_missing_fields(
        tenant,
        fiscal,
        config,
        token_configured=bool(_focus_environment_token(config, config.environment)),
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
    return _response_for(db, tenant_id, tenant, config)


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
    fiscal = _fiscal_config(db, tenant_id, tenant, create=True)
    missing = configuration_missing_fields(
        tenant,
        fiscal,
        config,
        token_configured=bool(_focus_environment_token(config, config.environment)),
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
        fiscal=fiscal,
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
        provider_response = FocusNfeProvider(
            config.environment,
            token=_focus_environment_token(config, config.environment),
        ).issue(reference, provider_payload)
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
    config = _config(db, tenant_id)
    if config is None:
        raise HTTPException(
            status_code=422, detail="Configuracao de NFS-e nao encontrada."
        )
    try:
        response = FocusNfeProvider(
            document.environment,
            token=_focus_environment_token(config, document.environment),
        ).query(document.reference)
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
        response = FocusNfeProvider(
            document.environment,
            token=_focus_environment_token(config, document.environment),
        ).cancel(document.reference, payload.justification.strip())
    except NfseProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    apply_provider_response(document, response)
    db.commit()
    db.refresh(document)
    return serialize_document(document)
