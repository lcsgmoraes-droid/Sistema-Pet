import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password
from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.models import Tenant, User, UserTenant
from app.routes.ecommerce_auth_cliente import (
    _digits_only,
    _get_or_create_cliente_for_user,
)
from app.routes.ecommerce_auth_common import (
    ECOMMERCE_TOKEN_TYPE,
    _create_ecommerce_session_tokens,
    _create_ecommerce_token_pair,
    _ecommerce_auth_payload,
    _ensure_active_store_access,
    _extract_tenant_id_from_request,
    _get_current_ecommerce_user,
    _normalize_tenant_uuid,
    _session_expiry_utc,
    _tenant_status_is_active,
    security,
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
    EcommerceRefreshTokenRequest,
    EcommerceRegisterRequest,
)
from app.routes.ecommerce_auth_settings import EMAIL_VERIFICATION_REQUIRED
from app.security.jwt_compat import JWTError, jwt
from app.services.auth_security import (
    is_user_locked,
    register_account_created,
    register_failed_login,
    register_logout,
    register_successful_login,
    remaining_lock_seconds,
)
from app.services.sales_channel import normalize_online_sales_channel
from app.session_manager import get_session_by_jti, revoke_session, validate_session
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

    auth_payload = _create_ecommerce_session_tokens(
        db=db,
        user=user,
        request=request,
        tenant_id=str(tenant_id),
    )

    return {
        **auth_payload,
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

    auth_payload = _create_ecommerce_session_tokens(
        db=db,
        user=user,
        request=request,
        tenant_id=str(tenant_id),
    )

    cliente = _get_or_create_cliente_for_user(db, user)
    db.commit()

    return {
        **auth_payload,
        "user": _serialize_profile(user, cliente, db),
    }


@router.post("/refresh")
def refresh_cliente(
    payload: EcommerceRefreshTokenRequest,
    db: Session = Depends(get_session),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token invalido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_payload = jwt.decode(
            payload.refresh_token, JWT_SECRET_KEY, algorithms=[ALGORITHM]
        )
    except JWTError:
        raise credentials_exception

    if (
        token_payload.get("typ") != "refresh"
        or token_payload.get("token_type") != ECOMMERCE_TOKEN_TYPE
    ):
        raise credentials_exception

    user_id = token_payload.get("sub")
    token_jti = token_payload.get("jti")
    tenant_id = token_payload.get("tenant_id")
    active_profile = token_payload.get("active_profile")
    if not user_id or not token_jti or not tenant_id:
        raise credentials_exception
    tenant_uuid = _normalize_tenant_uuid(tenant_id)
    if not tenant_uuid:
        raise credentials_exception

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise credentials_exception

    if not validate_session(db, token_jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao expirada ou revogada",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db_session = get_session_by_jti(db, token_jti)
    if (
        not db_session
        or db_session.user_id != user_id_int
        or str(db_session.tenant_id) != str(tenant_uuid)
    ):
        raise credentials_exception

    user = (
        db.query(User)
        .filter(User.id == user_id_int, User.tenant_id == tenant_uuid)
        .first()
    )
    if not user or not user.is_active:
        raise credentials_exception

    user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user.id,
            UserTenant.tenant_id == tenant_uuid,
            UserTenant.is_active.is_(True),
        )
        .first()
    )
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_uuid)).first()
    if not user_tenant or not tenant or not _tenant_status_is_active(tenant.status):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant inativo ou indisponivel",
        )

    access_token, refresh_token = _create_ecommerce_token_pair(
        user=user,
        token_jti=token_jti,
        expires_at=_session_expiry_utc(db_session),
        tenant_id=str(tenant_uuid),
        active_profile=active_profile,
    )
    return _ecommerce_auth_payload(access_token, refresh_token)


@router.post("/logout")
def logout_cliente(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    try:
        token_payload = jwt.decode(
            credentials.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_jti = token_payload.get("jti")
    revoked_count = 0
    db_session = get_session_by_jti(db, token_jti) if token_jti else None
    if db_session and db_session.user_id == current_user.id:
        if revoke_session(db, db_session.id, current_user.id, "ecommerce_logout"):
            revoked_count = 1

    register_logout(db, current_user, request, revoked_count)
    db.commit()
    return {"message": "Logout realizado com sucesso"}
