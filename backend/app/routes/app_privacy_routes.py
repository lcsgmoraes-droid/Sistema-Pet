from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Cliente, User
from app.routes.ecommerce_auth import _activate_user_tenant_context, _get_current_ecommerce_user
from app.services.lgpd_service import PREFERENCE_TYPES, PrivacyOpsService


router = APIRouter(prefix="/app/privacidade", tags=["App Mobile - Privacidade"])

REQUEST_TYPES = {"access", "export", "correction", "deletion", "revocation", "information"}


class AppPreferencesUpdate(BaseModel):
    marketing_email: Optional[bool] = None
    marketing_whatsapp: Optional[bool] = None
    marketing_sms: Optional[bool] = None
    marketing_push: Optional[bool] = None
    analytics: Optional[bool] = None


class AppPrivacyRequestCreate(BaseModel):
    request_type: str
    details: Optional[str] = None
    payload: Optional[dict] = None


def _request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _get_cliente_or_404(db: Session, user: User) -> Cliente:
    tenant_id = _activate_user_tenant_context(user)
    cliente = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.user_id == user.id)
        .first()
    )
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de cliente nao encontrado. Contate a loja.",
        )
    return cliente


def _service(db: Session, user: User) -> PrivacyOpsService:
    return PrivacyOpsService(db, _activate_user_tenant_context(user))


@router.get("/preferencias")
def minhas_preferencias_privacidade(
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    cliente = _get_cliente_or_404(db, current_user)
    service = _service(db, current_user)
    return {
        "cliente_id": cliente.id,
        "preferencias": service.current_preferences("customer", str(cliente.id)),
        "historico": service.consent_history("customer", str(cliente.id), limit=100),
    }


@router.put("/preferencias")
def atualizar_minhas_preferencias_privacidade(
    payload: AppPreferencesUpdate,
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    cliente = _get_cliente_or_404(db, current_user)
    preferences = {key: getattr(payload, key) for key in PREFERENCE_TYPES}
    if all(value is None for value in preferences.values()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe ao menos uma preferencia")

    service = _service(db, current_user)
    service.set_customer_preferences(
        cliente=cliente,
        preferences=preferences,
        actor_user_id=current_user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        source="app",
    )
    db.commit()
    return {
        "cliente_id": cliente.id,
        "preferencias": service.current_preferences("customer", str(cliente.id)),
    }


@router.get("/dossie")
def meu_dossie_privacidade(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    cliente = _get_cliente_or_404(db, current_user)
    return _service(db, current_user).export_customer_data(
        cliente_id=cliente.id,
        actor_user_id=current_user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        include_sales_limit=200,
    )


@router.post("/solicitacoes", status_code=status.HTTP_201_CREATED)
def criar_minha_solicitacao_privacidade(
    payload: AppPrivacyRequestCreate,
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    cliente = _get_cliente_or_404(db, current_user)
    request_type = payload.request_type.strip().lower()
    if request_type not in REQUEST_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de solicitacao LGPD invalido")

    service = _service(db, current_user)
    row = service.create_subject_request(
        subject_type="customer",
        subject_id=str(cliente.id),
        request_type=request_type,
        details=payload.details,
        requester_name=cliente.nome,
        requester_email=cliente.email or current_user.email,
        requester_phone=cliente.telefone or cliente.celular,
        channel="app",
        payload=payload.payload,
        created_by_user_id=current_user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return {"request": service._serialize_request(row)}


@router.get("/solicitacoes")
def listar_minhas_solicitacoes_privacidade(
    db: Session = Depends(get_session),
    current_user: User = Depends(_get_current_ecommerce_user),
):
    cliente = _get_cliente_or_404(db, current_user)
    return {
        "requests": _service(db, current_user).list_subject_requests(
            subject_type="customer",
            subject_id=str(cliente.id),
            limit=100,
        )
    }
