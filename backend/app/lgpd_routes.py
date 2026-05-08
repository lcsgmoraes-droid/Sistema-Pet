from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.services.lgpd_service import PREFERENCE_TYPES, PrivacyOpsService


router = APIRouter(prefix="/lgpd", tags=["LGPD"])

REQUEST_TYPES = {"access", "export", "correction", "deletion", "revocation", "information"}


class PreferencesUpdate(BaseModel):
    marketing_email: Optional[bool] = None
    marketing_whatsapp: Optional[bool] = None
    marketing_sms: Optional[bool] = None
    marketing_push: Optional[bool] = None
    analytics: Optional[bool] = None


class SubjectRequestCreate(BaseModel):
    subject_type: str = "customer"
    subject_id: str
    request_type: str
    details: Optional[str] = None
    requester_name: Optional[str] = None
    requester_email: Optional[str] = None
    requester_phone: Optional[str] = None
    channel: str = "erp"
    payload: Optional[dict] = None


class SubjectRequestProcess(BaseModel):
    status: str
    resolution_notes: Optional[str] = None
    response_payload: Optional[dict] = None


def _request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _service(db: Session, tenant_id) -> PrivacyOpsService:
    return PrivacyOpsService(db, str(tenant_id))


def _get_cliente(db: Session, tenant_id: str, cliente_id: int) -> Cliente:
    cliente = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == str(tenant_id), Cliente.id == cliente_id)
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nao encontrado")
    return cliente


@router.get("/status")
def lgpd_status(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    service = _service(db, tenant_id)
    pendentes = service.list_subject_requests(status="pending", limit=50)
    em_analise = service.list_subject_requests(status="in_review", limit=50)
    return {
        "pending": len(pendentes),
        "in_review": len(em_analise),
        "next_items": pendentes[:10],
    }


@router.get("/clientes/{cliente_id}/dossie")
def exportar_dossie_cliente(
    cliente_id: int,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    try:
        return _service(db, tenant_id).export_customer_data(
            cliente_id=cliente_id,
            actor_user_id=current_user.id,
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/clientes/{cliente_id}/consentimentos")
def listar_consentimentos_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    service = _service(db, tenant_id)
    _get_cliente(db, str(tenant_id), cliente_id)
    return {
        "cliente_id": cliente_id,
        "preferencias": service.current_preferences("customer", str(cliente_id)),
        "historico": service.consent_history("customer", str(cliente_id), limit=300),
    }


@router.put("/clientes/{cliente_id}/preferencias")
def atualizar_preferencias_cliente(
    cliente_id: int,
    payload: PreferencesUpdate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    cliente = _get_cliente(db, str(tenant_id), cliente_id)
    preferences = {key: getattr(payload, key) for key in PREFERENCE_TYPES}
    if all(value is None for value in preferences.values()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe ao menos uma preferencia")

    service = _service(db, tenant_id)
    service.set_customer_preferences(
        cliente=cliente,
        preferences=preferences,
        actor_user_id=current_user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        source="erp",
    )
    db.commit()
    return {
        "cliente_id": cliente_id,
        "preferencias": service.current_preferences("customer", str(cliente_id)),
    }


@router.post("/solicitacoes", status_code=status.HTTP_201_CREATED)
def criar_solicitacao_lgpd(
    payload: SubjectRequestCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    request_type = payload.request_type.strip().lower()
    if request_type not in REQUEST_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de solicitacao LGPD invalido")

    service = _service(db, tenant_id)
    row = service.create_subject_request(
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        request_type=request_type,
        details=payload.details,
        requester_name=payload.requester_name,
        requester_email=payload.requester_email,
        requester_phone=payload.requester_phone,
        channel=payload.channel or "erp",
        payload=payload.payload,
        created_by_user_id=current_user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return {"request": service._serialize_request(row)}


@router.get("/solicitacoes")
def listar_solicitacoes_lgpd(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    return {
        "requests": _service(db, tenant_id).list_subject_requests(
            status=status_filter,
            subject_type=subject_type,
            subject_id=subject_id,
            limit=limit,
        )
    }


@router.patch("/solicitacoes/{request_id}")
def processar_solicitacao_lgpd(
    request_id: int,
    payload: SubjectRequestProcess,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    service = _service(db, tenant_id)
    try:
        row = service.process_subject_request(
            request_id=request_id,
            status=payload.status,
            processed_by_user_id=current_user.id,
            resolution_notes=payload.resolution_notes,
            response_payload=payload.response_payload,
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return {"request": service._serialize_request(row)}
