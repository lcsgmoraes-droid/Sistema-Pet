from datetime import datetime, timedelta, timezone
from uuid import UUID
import os
import secrets
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.models import Cliente, Role, Tenant, User, UserTenant
from app.services.email_service import send_email


router = APIRouter(prefix="/ecommerce/auth", tags=["ecommerce-auth"])
security = HTTPBearer()

RESET_TOKEN_MINUTES = 30


class EcommerceRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    nome: str | None = None
    cpf: str = Field(min_length=11, max_length=14, description='CPF obrigatório (11 dígitos, com ou sem formatação)')


class EcommerceLoginRequest(BaseModel):
    email: EmailStr
    password: str


class EcommerceForgotPasswordRequest(BaseModel):
    email: EmailStr
    canal: str | None = None


class EcommerceResetPasswordRequest(BaseModel):
    token: str
    email: EmailStr | None = None
    nova_senha: str = Field(min_length=6)


class EcommerceProfileUpdateRequest(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    cpf: str | None = None
    cep: str | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    endereco_entrega: str | None = None
    usar_endereco_entrega_diferente: bool | None = None
    entrega_nome: str | None = None
    entrega_cep: str | None = None
    entrega_endereco: str | None = None
    entrega_numero: str | None = None
    entrega_complemento: str | None = None
    entrega_bairro: str | None = None
    entrega_cidade: str | None = None
    entrega_estado: str | None = None


def _normalize_tenant_uuid(raw_tenant_id: str | None) -> UUID | None:
    if not raw_tenant_id:
        return None
    try:
        return UUID(str(raw_tenant_id).strip())
    except Exception:
        return None


def _align_reference_datetime(target_dt: datetime, reference_dt: datetime) -> datetime:
    """
    Alinha o datetime de referência ao mesmo padrão (com/sem tz) do alvo.
    Evita TypeError quando o banco retorna datetime sem timezone.
    """
    if target_dt.tzinfo is None and reference_dt.tzinfo is not None:
        return reference_dt.replace(tzinfo=None)
    if target_dt.tzinfo is not None and reference_dt.tzinfo is None:
        return reference_dt.replace(tzinfo=timezone.utc)
    return reference_dt


def _is_expired(dt: datetime | None, now_ref: datetime) -> bool:
    if not dt:
        return False
    aligned_now = _align_reference_datetime(dt, now_ref)
    return dt < aligned_now


def _is_expired_or_equal(dt: datetime | None, now_ref: datetime) -> bool:
    if not dt:
        return False
    aligned_now = _align_reference_datetime(dt, now_ref)
    return dt <= aligned_now


def _remaining_days_until(dt: datetime, now_ref: datetime) -> int:
    aligned_now = _align_reference_datetime(dt, now_ref)
    return max(0, (dt - aligned_now).days)


def _extract_tenant_id_from_request(request: Request) -> UUID:
    tenant_id = _normalize_tenant_uuid(request.headers.get("X-Tenant-ID"))
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID obrigatório e deve ser UUID válido",
        )
    return tenant_id


def _build_storefront_reset_link(tenant: Tenant | None, user_email: str, reset_token: str) -> str:
    base_url = (os.getenv("ECOMMERCE_BASE_URL") or "https://mlprohub.com.br").rstrip("/")
    store_ref = None
    if tenant:
        store_ref = tenant.ecommerce_slug or tenant.id

    if store_ref:
        return (
            f"{base_url}/ecommerce?tenant={quote(str(store_ref))}"
            f"&recovery=1&email={quote(user_email)}&token={quote(reset_token)}"
        )

    return (
        f"{base_url}/ecommerce"
        f"?recovery=1&email={quote(user_email)}&token={quote(reset_token)}"
    )


def _resolve_password_recovery_channel(request: Request, payload: EcommerceForgotPasswordRequest) -> str:
    canal = (payload.canal or request.headers.get("X-Client-Channel") or "").strip().lower()
    if canal in {"app", "mobile", "site", "web", "loja"}:
        return "app" if canal in {"app", "mobile"} else "site"

    origin = (request.headers.get("origin") or "").lower()
    referer = (request.headers.get("referer") or "").lower()
    if origin or referer:
        return "site"

    user_agent = (request.headers.get("user-agent") or "").lower()
    if "okhttp" in user_agent or "expo" in user_agent or "reactnative" in user_agent:
        return "app"

    return "app"


def _build_reset_password_email_for_app(user: User, reset_token: str) -> tuple[str, str, str]:
        saudacao = f", {user.nome}" if getattr(user, "nome", None) else ""
        subject = "Recuperacao de senha do app - Pet Shop Pro"
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #1f2937; max-width: 620px; margin: 0 auto;">
                <div style="background: #2563eb; color: #ffffff; padding: 20px 24px; border-radius: 12px 12px 0 0;">
                    <h1 style="margin: 0; font-size: 22px;">Recuperar senha no app</h1>
                </div>
                <div style="border: 1px solid #dbeafe; border-top: none; border-radius: 0 0 12px 12px; padding: 24px;">
                    <p>Ola{saudacao}.</p>
                    <p>Recebemos um pedido para redefinir a sua senha no aplicativo.</p>
                    <p>Abra o app, entre na tela <strong>Recuperar senha</strong> e use o token abaixo:</p>
                    <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 16px; margin: 18px 0;">
                        <div style="font-size: 13px; color: #1d4ed8; margin-bottom: 6px;">Token de recuperacao</div>
                        <div style="font-size: 20px; font-weight: 700; letter-spacing: 0.4px; word-break: break-all;">{reset_token}</div>
                    </div>
                    <p>Esse token expira em <strong>{RESET_TOKEN_MINUTES} minutos</strong>.</p>
                    <p>Este e-mail e valido apenas para a recuperacao dentro do app.</p>
                    <p>Se voce nao pediu essa alteracao, pode ignorar este e-mail com seguranca.</p>
                </div>
            </body>
        </html>
        """
        text_body = (
                "Recuperacao de senha do app - Pet Shop Pro\n\n"
                "Abra o app e use este token na tela Recuperar senha:\n"
                f"{reset_token}\n\n"
                f"Validade: {RESET_TOKEN_MINUTES} minutos.\n"
                "Se voce nao pediu essa alteracao, ignore este e-mail."
        )
        return subject, html_body, text_body


def _build_reset_password_email_for_site(user: User, reset_token: str, reset_link: str) -> tuple[str, str, str]:
        saudacao = f", {user.nome}" if getattr(user, "nome", None) else ""
        subject = "Recuperacao de senha da loja - Pet Shop Pro"
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #1f2937; max-width: 620px; margin: 0 auto;">
                <div style="background: #2563eb; color: #ffffff; padding: 20px 24px; border-radius: 12px 12px 0 0;">
                    <h1 style="margin: 0; font-size: 22px;">Recuperar senha na loja online</h1>
                </div>
                <div style="border: 1px solid #dbeafe; border-top: none; border-radius: 0 0 12px 12px; padding: 24px;">
                    <p>Ola{saudacao}.</p>
                    <p>Recebemos um pedido para redefinir a sua senha na loja online.</p>
                    <p>Abra a recuperacao direto pela loja:</p>
                    <p style="margin: 18px 0;">
                        <a href="{reset_link}"
                             style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 18px; border-radius: 10px; font-weight: 700;">
                            Recuperar senha agora
                        </a>
                    </p>
                    <p>Se preferir, voce tambem pode usar este token na tela de recuperacao da propria loja online:</p>
                    <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 16px; margin: 18px 0;">
                        <div style="font-size: 13px; color: #1d4ed8; margin-bottom: 6px;">Token de recuperacao</div>
                        <div style="font-size: 20px; font-weight: 700; letter-spacing: 0.4px; word-break: break-all;">{reset_token}</div>
                    </div>
                    <p>Esse token expira em <strong>{RESET_TOKEN_MINUTES} minutos</strong>.</p>
                    <p>Este e-mail e valido apenas para a recuperacao pela loja online.</p>
                    <p>Se voce nao pediu essa alteracao, pode ignorar este e-mail com seguranca.</p>
                </div>
            </body>
        </html>
        """
        text_body = (
                "Recuperacao de senha da loja - Pet Shop Pro\n\n"
                "Abra a recuperacao no link abaixo:\n"
                f"{reset_link}\n\n"
                "Ou use este token na tela de recuperacao da loja online:\n"
                f"{reset_token}\n\n"
                f"Validade: {RESET_TOKEN_MINUTES} minutos.\n"
                "Se voce nao pediu essa alteracao, ignore este e-mail."
        )
        return subject, html_body, text_body


def _get_current_ecommerce_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        token_type = payload.get("token_type")
        if token_type != "ecommerce_customer":
            raise credentials_exception
    except (JWTError, TypeError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception

    return user


def _digits_only(value: str | None) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _find_cliente_match(
    db: Session,
    *,
    tenant_id: str,
    user_id: int,
    email: str | None = None,
    cpf: str | None = None,
    telefone: str | None = None,
    exclude_cliente_id: int | None = None,
) -> Cliente | None:
    linked_query = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.user_id == user_id,
    )

    base_query = db.query(Cliente).filter(Cliente.tenant_id == tenant_id)

    if exclude_cliente_id is not None:
        base_query = base_query.filter(Cliente.id != exclude_cliente_id)

    cpf_digits = _digits_only(cpf)
    if cpf_digits:
        # Busca exata pelo CPF já normalizado (como salvo no banco)
        linked_by_cpf = linked_query.filter(Cliente.cpf == cpf_digits).first()
        if linked_by_cpf:
            return linked_by_cpf

        matched_by_cpf = base_query.filter(Cliente.cpf == cpf_digits).first()
        if matched_by_cpf:
            return matched_by_cpf

        # Fallback: busca normalizada por dígitos (para registros com CPF formatado no banco)
        cpf_candidates = base_query.filter(Cliente.cpf.isnot(None)).all()
        for candidate in cpf_candidates:
            if _digits_only(candidate.cpf) == cpf_digits:
                return candidate

    email = (email or "").strip().lower()
    if email:
        linked_by_email = linked_query.filter(Cliente.email == email).first()
        if linked_by_email:
            return linked_by_email

        matched_by_email = base_query.filter(Cliente.email == email).first()
        if matched_by_email:
            return matched_by_email

    telefone_digits = _digits_only(telefone)
    if telefone_digits:
        linked_phone_candidates = linked_query.filter(Cliente.telefone.isnot(None)).all()
        for candidate in linked_phone_candidates:
            if _digits_only(candidate.telefone) == telefone_digits:
                return candidate

        phone_candidates = base_query.filter(Cliente.telefone.isnot(None)).all()
        for candidate in phone_candidates:
            if _digits_only(candidate.telefone) == telefone_digits:
                return candidate

    return None


def _extract_ecommerce_delivery_details(cliente: Cliente | None) -> dict:
    default = {
        "usar_endereco_entrega_diferente": False,
        "entrega_nome": "",
        "entrega_cep": "",
        "entrega_endereco": "",
        "entrega_numero": "",
        "entrega_complemento": "",
        "entrega_bairro": "",
        "entrega_cidade": "",
        "entrega_estado": "",
    }
    if not cliente:
        return default

    raw = cliente.enderecos_adicionais
    if isinstance(raw, dict):
        details = raw.get("ecommerce_entrega")
        if isinstance(details, dict):
            return {**default, **details, "usar_endereco_entrega_diferente": True}

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("tipo") == "ecommerce_entrega":
                return {**default, **item, "usar_endereco_entrega_diferente": True}

    return default


def _upsert_delivery_details(cliente: Cliente, details: dict, enabled: bool) -> None:
    current = cliente.enderecos_adicionais
    items = []
    if isinstance(current, list):
        items = [item for item in current if not (isinstance(item, dict) and item.get("tipo") == "ecommerce_entrega")]

    if enabled:
        items.append({"tipo": "ecommerce_entrega", **details})
        cliente.enderecos_adicionais = items
    else:
        cliente.enderecos_adicionais = items if items else None


def _get_or_create_cliente_for_user(db: Session, user: User) -> Cliente:
    tenant_id = str(user.tenant_id)
    cliente = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.user_id == user.id)
        .first()
    )

    if not cliente:
        cliente = _find_cliente_match(
            db,
            tenant_id=tenant_id,
            user_id=user.id,
            email=user.email,
            cpf=user.cpf_cnpj,
            telefone=user.telefone,
        )

    if not cliente:
        cliente = Cliente(
            tenant_id=tenant_id,
            user_id=user.id,
            nome=user.nome or user.email,
            email=user.email,
            telefone=user.telefone,
            cpf=user.cpf_cnpj,
            tipo_cadastro="cliente",
            tipo_pessoa="PF",
            ativo=True,
        )
        db.add(cliente)
        db.flush()
    else:
        cliente.user_id = user.id
        if not cliente.nome:
            cliente.nome = user.nome or user.email
        if not cliente.email:
            cliente.email = user.email
        if not cliente.telefone and user.telefone:
            cliente.telefone = user.telefone
        if not cliente.cpf and user.cpf_cnpj:
            cliente.cpf = user.cpf_cnpj

    return cliente


def _get_or_create_customer_role(db: Session, tenant_id: str) -> Role:
    role = (
        db.query(Role)
        .filter(Role.tenant_id == tenant_id, Role.name == "Cliente")
        .first()
    )
    if role:
        return role

    role = Role(name="Cliente", tenant_id=tenant_id)
    db.add(role)
    db.flush()
    return role


def _ensure_active_store_access(db: Session, user: User, tenant_id: str) -> UserTenant:
    vinculo = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user.id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )

    if vinculo and vinculo.is_active:
        return vinculo

    role = _get_or_create_customer_role(db, tenant_id)

    if vinculo:
        vinculo.role_id = role.id
        vinculo.is_active = True
        return vinculo

    vinculo = UserTenant(
        user_id=user.id,
        tenant_id=tenant_id,
        role_id=role.id,
        is_active=True,
    )
    db.add(vinculo)
    db.flush()
    return vinculo


def _serialize_profile(user: User, cliente: Cliente | None) -> dict:
    delivery = _extract_ecommerce_delivery_details(cliente)
    return {
        "id": user.id,
        "email": user.email,
        "nome": user.nome,
        "telefone": (cliente.telefone if cliente else None) or user.telefone,
        "cpf": (cliente.cpf if cliente else None) or user.cpf_cnpj,
        "cep": cliente.cep if cliente else None,
        "endereco": cliente.endereco if cliente else None,
        "numero": cliente.numero if cliente else None,
        "complemento": cliente.complemento if cliente else None,
        "bairro": cliente.bairro if cliente else None,
        "cidade": cliente.cidade if cliente else None,
        "estado": cliente.estado if cliente else None,
        "endereco_entrega": cliente.endereco_entrega if cliente else None,
        "usar_endereco_entrega_diferente": delivery.get("usar_endereco_entrega_diferente", False),
        "endereco_entrega_detalhado": {
            "entrega_nome": delivery.get("entrega_nome", ""),
            "entrega_cep": delivery.get("entrega_cep", ""),
            "entrega_endereco": delivery.get("entrega_endereco", ""),
            "entrega_numero": delivery.get("entrega_numero", ""),
            "entrega_complemento": delivery.get("entrega_complemento", ""),
            "entrega_bairro": delivery.get("entrega_bairro", ""),
            "entrega_cidade": delivery.get("entrega_cidade", ""),
            "entrega_estado": delivery.get("entrega_estado", ""),
        },
        "cliente_id": cliente.id if cliente else None,
        # Perfil entregador — usado pelo app mobile para mostrar interface correta
        "is_entregador": cliente.is_entregador if cliente else False,
        "funcionario_id": cliente.id if (cliente and cliente.is_entregador) else None,
    }


@router.post("/registrar")
def registrar_cliente(payload: EcommerceRegisterRequest, request: Request, db: Session = Depends(get_session)):
    tenant_id = _extract_tenant_id_from_request(request)

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")

    # Normaliza CPF para apenas dígitos antes de salvar e de buscar o Cliente
    cpf_normalizado = re.sub(r"\D+", "", str(payload.cpf or "")).strip() or None

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        nome=payload.nome,
        is_active=True,
        is_admin=False,
        consent_date=datetime.now(timezone.utc),
        tenant_id=tenant_id,
        cpf_cnpj=cpf_normalizado,  # Salva o CPF antes para que _get_or_create_cliente_for_user possa encontrar o Cliente por CPF
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    cliente = _get_or_create_cliente_for_user(db, user)
    if payload.nome:
        cliente.nome = payload.nome
    if cpf_normalizado and not cliente.cpf:
        cliente.cpf = cpf_normalizado
    _ensure_active_store_access(db, user, str(tenant_id))
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
                "canal": "app",
                "email": user.email,
            },
        )
        db.add(evento_campanha)
        db.commit()
    except Exception as e_camp:
        import logging
        logging.getLogger(__name__).error("[Campanhas] Erro ao publicar customer_registered: %s", e_camp)

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
        "user": _serialize_profile(user, cliente),
    }


@router.post("/login")
def login_cliente(payload: EcommerceLoginRequest, request: Request, db: Session = Depends(get_session)):
    tenant_id = _extract_tenant_id_from_request(request)
    email = payload.email.strip().lower()

    user = (
        db.query(User)
        .filter(User.email == email, User.tenant_id == tenant_id)
        .first()
    )

    if not user or not verify_password(payload.password, user.hashed_password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta inativa")

    _ensure_active_store_access(db, user, str(tenant_id))
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
        "user": _serialize_profile(user, cliente),
    }


@router.post("/esqueci-senha")
def esqueci_senha(payload: EcommerceForgotPasswordRequest, request: Request, db: Session = Depends(get_session)):
    tenant_id = _extract_tenant_id_from_request(request)
    email = payload.email.strip().lower()
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()

    user = (
        db.query(User)
        .filter(User.email == email, User.tenant_id == tenant_id)
        .first()
    )

    if user and user.is_active:
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_MINUTES)
        reset_link = _build_storefront_reset_link(tenant, user.email, reset_token)
        canal = _resolve_password_recovery_channel(request, payload)
        if canal == "site":
            subject, html_body, text_body = _build_reset_password_email_for_site(user, reset_token, reset_link)
        else:
            subject, html_body, text_body = _build_reset_password_email_for_app(user, reset_token)
        enviado = send_email(
            to=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            simulate_if_unconfigured=False,
        )
        if not enviado:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível enviar o e-mail de recuperação agora. Tente novamente em instantes.",
            )
        db.commit()
        return {
            "message": "Se o email existir, enviaremos instruções de recuperação.",
            "expires_in_minutes": RESET_TOKEN_MINUTES,
        }

    return {"message": "Se o email existir, enviaremos instruções de recuperação."}


@router.post("/resetar-senha")
def resetar_senha(payload: EcommerceResetPasswordRequest, db: Session = Depends(get_session)):
    query = db.query(User).filter(User.reset_token == payload.token)
    if payload.email:
        query = query.filter(User.email == payload.email.strip().lower())
    user = query.first()

    if not user or not user.reset_token_expires:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido")

    if user.reset_token_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expirado")

    user.hashed_password = hash_password(payload.nova_senha)
    user.reset_token = None
    user.reset_token_expires = None
    _ensure_active_store_access(db, user, str(user.tenant_id))
    db.commit()

    return {"message": "Senha atualizada com sucesso"}


@router.get("/me")
def me(current_user: User = Depends(_get_current_ecommerce_user), db: Session = Depends(get_session)):
    cliente = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == str(current_user.tenant_id), Cliente.user_id == current_user.id)
        .first()
    )
    data = _serialize_profile(current_user, cliente)
    data["is_active"] = current_user.is_active
    return data


@router.get("/perfil")
def obter_perfil(current_user: User = Depends(_get_current_ecommerce_user), db: Session = Depends(get_session)):
    cliente = _get_or_create_cliente_for_user(db, current_user)
    db.commit()
    return _serialize_profile(current_user, cliente)


@router.put("/perfil")
def atualizar_perfil(
    payload: EcommerceProfileUpdateRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    cliente = _get_or_create_cliente_for_user(db, current_user)

    nome_informado = (payload.nome or "").strip()
    nome_atual = (current_user.nome or "").strip()
    nome_final = nome_informado or nome_atual
    if not nome_final:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome completo obrigatório")
    if nome_informado and nome_informado != nome_atual and " " not in nome_final:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe nome completo (nome e sobrenome)")

    current_user.nome = nome_final
    cliente.nome = nome_final

    if payload.telefone is not None:
        telefone = payload.telefone.strip()
        current_user.telefone = telefone or None
        cliente.telefone = telefone or None

    if payload.cpf is not None:
        cpf = payload.cpf.strip()
        current_user.cpf_cnpj = cpf or None
        cliente.cpf = cpf or None

    potential_match = _find_cliente_match(
        db,
        tenant_id=str(current_user.tenant_id),
        user_id=current_user.id,
        email=current_user.email,
        cpf=current_user.cpf_cnpj,
        telefone=current_user.telefone,
        exclude_cliente_id=cliente.id,
    )

    if potential_match and potential_match.id != cliente.id:
        previous_cliente = cliente
        if not potential_match.nome and cliente.nome:
            potential_match.nome = cliente.nome
        if not potential_match.email and cliente.email:
            potential_match.email = cliente.email
        if not potential_match.telefone and cliente.telefone:
            potential_match.telefone = cliente.telefone
        if not potential_match.cpf and cliente.cpf:
            potential_match.cpf = cliente.cpf
        if not potential_match.endereco and cliente.endereco:
            potential_match.endereco = cliente.endereco
        if not potential_match.cep and cliente.cep:
            potential_match.cep = cliente.cep
        if not potential_match.numero and cliente.numero:
            potential_match.numero = cliente.numero
        if not potential_match.complemento and cliente.complemento:
            potential_match.complemento = cliente.complemento
        if not potential_match.bairro and cliente.bairro:
            potential_match.bairro = cliente.bairro
        if not potential_match.cidade and cliente.cidade:
            potential_match.cidade = cliente.cidade
        if not potential_match.estado and cliente.estado:
            potential_match.estado = cliente.estado
        if not potential_match.endereco_entrega and cliente.endereco_entrega:
            potential_match.endereco_entrega = cliente.endereco_entrega

        potential_match.user_id = current_user.id
        cliente = potential_match
        db.delete(previous_cliente)

    if payload.endereco is not None:
        cliente.endereco = payload.endereco.strip() or None
    if payload.cep is not None:
        cliente.cep = payload.cep.strip() or None
    if payload.numero is not None:
        cliente.numero = payload.numero.strip() or None
    if payload.complemento is not None:
        cliente.complemento = payload.complemento.strip() or None
    if payload.bairro is not None:
        cliente.bairro = payload.bairro.strip() or None
    if payload.cidade is not None:
        cliente.cidade = payload.cidade.strip() or None
    if payload.estado is not None:
        cliente.estado = payload.estado.strip() or None
    if payload.endereco_entrega is not None:
        cliente.endereco_entrega = payload.endereco_entrega.strip() or None

    if payload.usar_endereco_entrega_diferente is not None:
        enabled = bool(payload.usar_endereco_entrega_diferente)

        if enabled:
            entrega_nome = (payload.entrega_nome or "").strip()
            entrega_endereco = (payload.entrega_endereco or "").strip()
            entrega_numero = (payload.entrega_numero or "").strip()
            entrega_bairro = (payload.entrega_bairro or "").strip()
            entrega_cidade = (payload.entrega_cidade or "").strip()
            entrega_estado = (payload.entrega_estado or "").strip()
            entrega_cep = (payload.entrega_cep or "").strip()
            entrega_complemento = (payload.entrega_complemento or "").strip()

            if not entrega_nome:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o nome completo para entrega")
            if not entrega_endereco or not entrega_numero or not entrega_bairro or not entrega_cidade or not entrega_estado:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preencha o endereço de entrega completo")

            address_line = f"{entrega_endereco}, {entrega_numero}"
            tail = " | ".join(
                [
                    f"Bairro: {entrega_bairro}",
                    f"Cidade: {entrega_cidade}/{entrega_estado}",
                    f"CEP: {entrega_cep}" if entrega_cep else "",
                    f"Compl.: {entrega_complemento}" if entrega_complemento else "",
                    f"Destinatário: {entrega_nome}",
                ]
            )
            cliente.endereco_entrega = " | ".join([address_line, *[part for part in tail.split(" | ") if part]])

            _upsert_delivery_details(
                cliente,
                {
                    "entrega_nome": entrega_nome,
                    "entrega_cep": entrega_cep,
                    "entrega_endereco": entrega_endereco,
                    "entrega_numero": entrega_numero,
                    "entrega_complemento": entrega_complemento,
                    "entrega_bairro": entrega_bairro,
                    "entrega_cidade": entrega_cidade,
                    "entrega_estado": entrega_estado,
                },
                True,
            )
        else:
            _upsert_delivery_details(cliente, {}, False)

    db.commit()
    db.refresh(current_user)
    db.refresh(cliente)
    return _serialize_profile(current_user, cliente)


@router.get("/meus-cupons")
def meus_cupons(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna os cupons ativos do cliente autenticado no app.
    """
    from app.campaigns.models import Coupon, CouponStatusEnum

    cliente = _get_or_create_cliente_for_user(db, current_user)

    cupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == current_user.tenant_id,
            Coupon.customer_id == cliente.id,
            Coupon.status == CouponStatusEnum.active,
        )
        .order_by(Coupon.created_at.desc())
        .all()
    )

    now = datetime.now(timezone.utc)
    resultado = []
    for c in cupons:
        expirado = _is_expired(c.valid_until, now)
        resultado.append({
            "id": c.id,
            "code": c.code,
            "coupon_type": c.coupon_type.value,
            "discount_value": float(c.discount_value) if c.discount_value else None,
            "discount_percent": float(c.discount_percent) if c.discount_percent else None,
            "valid_until": c.valid_until.isoformat() if c.valid_until else None,
            "expirado": expirado,
            "min_purchase_value": float(c.min_purchase_value) if c.min_purchase_value else None,
        })

    return resultado


@router.get("/meus-beneficios")
def meus_beneficios(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna em uma única chamada tudo que o app precisa para montar
    a tela 'Meus Benefícios': ranking, carimbos, cashback e cupons ativos.
    """
    from sqlalchemy import func as sqlfunc
    from app.campaigns.models import (
        CashbackTransaction,
        Campaign,
        CampaignTypeEnum,
        Coupon,
        CouponStatusEnum,
        CustomerRankHistory,
    )
    from app.campaigns.loyalty_service import summarize_loyalty_balances_for_customer

    cliente = _get_or_create_cliente_for_user(db, current_user)
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    # --- Cashback ---
    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            or_(
                CashbackTransaction.expires_at.is_(None),
                CashbackTransaction.expires_at > now,
                CashbackTransaction.tx_type != "credit",
            ),
        )
        .scalar()
    )
    saldo_cashback = float(saldo_raw or 0)

    # --- Carimbos ---
    loyalty_summary = summarize_loyalty_balances_for_customer(
        db,
        tenant_id=tenant_id,
        customer_id=cliente.id,
    )
    loyalty_campaign = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.loyalty_stamp,
        )
        .first()
    )
    stamps_to_complete = int((loyalty_campaign.params or {}).get("stamps_to_complete", 10)) if loyalty_campaign else 10
    min_purchase_value = float((loyalty_campaign.params or {}).get("min_purchase_value", 0) or 0) if loyalty_campaign else 0.0
    saldo_total_carimbos = int(loyalty_summary.get("total_carimbos") or 0)
    carimbos_no_cartao = max(saldo_total_carimbos, 0)

    # --- Ranking ---
    rank_atual = (
        db.query(CustomerRankHistory)
        .filter(
            CustomerRankHistory.tenant_id == tenant_id,
            CustomerRankHistory.customer_id == cliente.id,
        )
        .order_by(CustomerRankHistory.period.desc())
        .first()
    )
    rank_level = rank_atual.rank_level.value if rank_atual else "bronze"
    rank_total_spent = float(rank_atual.total_spent) if rank_atual else 0.0
    rank_total_purchases = rank_atual.total_purchases if rank_atual else 0

    ranking_campaign = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.ranking_monthly,
        )
        .first()
    )
    rp = ranking_campaign.params if ranking_campaign else {}
    ranking_thresholds = {
        "silver_min_spent": float(rp.get("silver_min_spent", 300)),
        "silver_min_purchases": int(rp.get("silver_min_purchases", 4)),
        "silver_min_months": int(rp.get("silver_min_months", 2)),
        "gold_min_spent": float(rp.get("gold_min_spent", 1000)),
        "gold_min_purchases": int(rp.get("gold_min_purchases", 10)),
        "gold_min_months": int(rp.get("gold_min_months", 4)),
        "diamond_min_spent": float(rp.get("diamond_min_spent", 3000)),
        "diamond_min_purchases": int(rp.get("diamond_min_purchases", 20)),
        "diamond_min_months": int(rp.get("diamond_min_months", 6)),
        "platinum_min_spent": float(rp.get("platinum_min_spent", 8000)),
        "platinum_min_purchases": int(rp.get("platinum_min_purchases", 40)),
        "platinum_min_months": int(rp.get("platinum_min_months", 10)),
    }

    # --- Cupons ativos ---
    cupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.customer_id == cliente.id,
            Coupon.status == CouponStatusEnum.active,
        )
        .order_by(Coupon.created_at.desc())
        .all()
    )
    cupons_lista = []
    for c in cupons:
        expirado = _is_expired(c.valid_until, now)
        cupons_lista.append({
            "id": c.id,
            "code": c.code,
            "coupon_type": c.coupon_type.value,
            "discount_value": float(c.discount_value) if c.discount_value else None,
            "discount_percent": float(c.discount_percent) if c.discount_percent else None,
            "valid_until": c.valid_until.isoformat() if c.valid_until else None,
            "expirado": expirado,
            "min_purchase_value": float(c.min_purchase_value) if c.min_purchase_value else None,
        })

    return {
        "cashback": {
            "saldo": saldo_cashback,
        },
        "carimbos": {
            "total_geral": saldo_total_carimbos,
            "carimbos_no_cartao": carimbos_no_cartao,
            "carimbos_ativos_brutos": int(loyalty_summary.get("total_carimbos_brutos") or 0),
            "carimbos_comprometidos_total": int(loyalty_summary.get("carimbos_comprometidos_total") or 0),
            "carimbos_convertidos": int(loyalty_summary.get("carimbos_convertidos") or 0),
            "carimbos_em_debito": int(loyalty_summary.get("carimbos_em_debito") or 0),
            "meta": stamps_to_complete,
            "min_purchase_value": min_purchase_value,
        },
        "ranking": {
            "nivel": rank_level,
            "total_spent": rank_total_spent,
            "total_purchases": rank_total_purchases,
            "thresholds": ranking_thresholds,
        },
        "cupons": cupons_lista,
    }


# ---------------------------------------------------------------------------
# Cashback — extrato (app mobile)
# ---------------------------------------------------------------------------

@router.get("/cashback/extrato")
def meu_extrato_cashback(
    limit: int = 50,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna o extrato de cashback do cliente autenticado no app.
    """
    from sqlalchemy import func as sqlfunc
    from app.campaigns.models import CashbackTransaction, CashbackSourceTypeEnum

    cliente = _get_or_create_cliente_for_user(db, current_user)
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    txs = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
        )
        .order_by(CashbackTransaction.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )

    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            or_(
                CashbackTransaction.expires_at.is_(None),
                CashbackTransaction.expires_at > now,
                CashbackTransaction.tx_type != "credit",
            ),
        )
        .scalar()
    )
    saldo_atual = float(saldo_raw or 0)

    items = []
    for t in txs:
        is_expired_credit = (
            getattr(t, "tx_type", "credit") == "credit"
            and t.expires_at is not None
            and _is_expired_or_equal(t.expires_at, now)
        )
        items.append({
            "id": t.id,
            "amount": float(t.amount),
            "tx_type": getattr(t, "tx_type", "credit"),
            "source_type": t.source_type.value,
            "description": t.description,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            "expired": is_expired_credit,
        })

    return {"saldo_atual": saldo_atual, "transacoes": items}


# ---------------------------------------------------------------------------
# Cashback — sugestão inteligente de pedido (app mobile)
# ---------------------------------------------------------------------------

@router.get("/cashback/sugestao")
def minha_sugestao_cashback(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna sugestão de compra baseada no padrão do cliente + saldo de cashback.
    """
    from sqlalchemy import func as sqlfunc
    from app.campaigns.models import CashbackTransaction, CashbackSourceTypeEnum

    cliente = _get_or_create_cliente_for_user(db, current_user)
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            sqlfunc.or_(
                CashbackTransaction.expires_at.is_(None),
                CashbackTransaction.expires_at > now,
                CashbackTransaction.tx_type != "credit",
            ),
        )
        .scalar()
    )
    saldo = float(saldo_raw or 0)

    # Ticket médio estimado pelas últimas compras com cashback
    ultimas = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            CashbackTransaction.tx_type == "credit" if hasattr(CashbackTransaction, "tx_type") else True,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.campaign,
        )
        .order_by(CashbackTransaction.created_at.desc())
        .limit(10)
        .all()
    )
    ticket_sugerido = round(
        sum(float(t.amount) for t in ultimas) / len(ultimas) * 50, 2
    ) if ultimas else 100.0

    valor_com_cashback = max(0.0, round(ticket_sugerido - saldo, 2))

    proximo_expirando = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            CashbackTransaction.tx_type == "credit" if hasattr(CashbackTransaction, "tx_type") else True,
            CashbackTransaction.expires_at.isnot(None),
            CashbackTransaction.expires_at > now,
        )
        .order_by(CashbackTransaction.expires_at.asc())
        .first()
    )

    return {
        "saldo_disponivel": saldo,
        "ticket_sugerido": ticket_sugerido,
        "valor_com_cashback": valor_com_cashback,
        "economia": min(saldo, ticket_sugerido),
        "proximo_expirando": {
            "amount": float(proximo_expirando.amount),
            "expires_at": proximo_expirando.expires_at.isoformat(),
            "dias_restantes": _remaining_days_until(proximo_expirando.expires_at, now),
        } if proximo_expirando else None,
    }

