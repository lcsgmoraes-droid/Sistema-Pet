import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.db import get_session
from app.models import User
from app.routes.ecommerce_auth_cliente import (
    _digits_only,
    _get_or_create_cliente_for_user,
)
from app.routes.ecommerce_auth_common import (
    _ensure_active_store_access,
    _extract_tenant_id_from_request,
)
from app.routes.ecommerce_auth_profiles import _serialize_profile
from app.routes.ecommerce_auth_recovery import (
    _email_verification_block,
    _mark_user_consent,
    _now_utc,
    _send_email_verification,
)
from app.routes.ecommerce_auth_schemas import (
    EcommerceLoginRequest,
    EcommerceRegisterRequest,
)
from app.routes.ecommerce_auth_settings import EMAIL_VERIFICATION_REQUIRED
from app.services.auth_security import (
    is_user_locked,
    register_account_created,
    register_failed_login,
    register_successful_login,
    remaining_lock_seconds,
)
from app.services.sales_channel import normalize_online_sales_channel
from app.tenancy.rls import sync_rls_auth_email


router = APIRouter()


@router.post("/registrar")
def registrar_cliente(
    payload: EcommerceRegisterRequest,
    request: Request,
    db: Session = Depends(get_session),
):
    tenant_id = _extract_tenant_id_from_request(request)
    email = payload.email.strip().lower()
    nome = (payload.nome or "").strip()
    canal_registro = normalize_online_sales_channel(
        payload.canal or request.headers.get("X-Client-Channel") or ""
    )

    if len(nome.split()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe nome completo (nome e sobrenome)",
        )

    if not payload.accepted_terms or not payload.accepted_privacy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aceite os Termos de Uso e a Politica de Privacidade para criar a conta.",
        )

    sync_rls_auth_email(db, email)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado"
        )

    # Normaliza CPF para apenas dígitos antes de salvar e de buscar o Cliente
    cpf_normalizado = re.sub(r"\D+", "", str(payload.cpf or "")).strip() or None
    telefone = (payload.telefone or "").strip()
    if len(_digits_only(telefone)) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone obrigatorio"
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        nome=nome,
        telefone=telefone,
        is_active=True,
        is_admin=False,
        email_verified=not EMAIL_VERIFICATION_REQUIRED,
        email_verified_at=_now_utc() if not EMAIL_VERIFICATION_REQUIRED else None,
        tenant_id=tenant_id,
        cpf_cnpj=cpf_normalizado,  # Salva o CPF antes para que _get_or_create_cliente_for_user possa encontrar o Cliente por CPF
    )
    _mark_user_consent(user, request, payload.terms_version, payload.privacy_version)
    db.add(user)
    if EMAIL_VERIFICATION_REQUIRED:
        enviado = _send_email_verification(user, canal_registro)
        if not enviado:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Nao foi possivel enviar o e-mail de confirmacao agora. Tente novamente em instantes.",
            )
    db.commit()
    db.refresh(user)

    cliente = _get_or_create_cliente_for_user(db, user)
    if nome:
        cliente.nome = nome
    if cpf_normalizado and not cliente.cpf:
        cliente.cpf = cpf_normalizado
    cliente.telefone = telefone
    _ensure_active_store_access(db, user, str(tenant_id))
    register_account_created(db, user, request, canal_registro)
    db.commit()
    db.refresh(cliente)

    # 🎯 CAMPANHAS — Publicar evento customer_registered na fila
    # Disparado tanto pelo app-mobile quanto pelo ecommerce (mesmo endpoint)
    # Ativa WelcomeHandler (cupom de boas-vindas) se houver campanha ativa
    try:
        from app.campaigns.models import CampaignEventQueue, EventOriginEnum

        evento_campanha = CampaignEventQueue(
            tenant_id=tenant_id,
            event_type="customer_registered",
            event_origin=EventOriginEnum.user_action,
            event_depth=0,
            payload={
                "customer_id": cliente.id,
                "canal": canal_registro,
                "email": user.email,
            },
        )
        db.add(evento_campanha)
        db.commit()
    except Exception as e_camp:
        import logging

        logging.getLogger(__name__).error(
            "[Campanhas] Erro ao publicar customer_registered: %s", e_camp
        )

    if EMAIL_VERIFICATION_REQUIRED:
        return {
            "access_token": None,
            "token_type": "bearer",
            "requires_email_verification": True,
            "email_verification_sent": True,
            "user": _serialize_profile(user, cliente, db),
        }

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "token_type": "ecommerce_customer",
        },
        tenant_id=str(tenant_id),
        role="customer",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _serialize_profile(user, cliente, db),
    }


@router.post("/login")
def login_cliente(
    payload: EcommerceLoginRequest, request: Request, db: Session = Depends(get_session)
):
    tenant_id = _extract_tenant_id_from_request(request)
    email = payload.email.strip().lower()

    user = (
        db.query(User).filter(User.email == email, User.tenant_id == tenant_id).first()
    )

    if user and is_user_locked(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas de login. Aguarde {max(1, remaining_lock_seconds(user) // 60)} minuto(s) e tente novamente.",
            headers={"Retry-After": str(remaining_lock_seconds(user))},
        )

    if not user or not verify_password(payload.password, user.hashed_password or ""):
        if user:
            register_failed_login(db, user, request)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Conta inativa"
        )

    if _email_verification_block(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email ainda nao confirmado. Verifique sua caixa de entrada ou solicite um novo link.",
        )

    _ensure_active_store_access(db, user, str(tenant_id))
    register_successful_login(db, user, request)
    db.commit()

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "token_type": "ecommerce_customer",
        },
        tenant_id=str(tenant_id),
        role="customer",
    )

    cliente = _get_or_create_cliente_for_user(db, user)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _serialize_profile(user, cliente, db),
    }
