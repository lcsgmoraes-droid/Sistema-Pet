import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password
from app.db import get_session
from app.models import Cliente, User
from app.routes.ecommerce_auth_cliente import (
    _digits_only,
    _get_or_create_cliente_for_user,
    _phone_digits,
    _select_preferred_cliente,
)
from app.routes.ecommerce_auth_common import (
    _create_ecommerce_session_tokens,
    _ensure_active_store_access,
    _extract_tenant_id_from_request,
    _refresh_ecommerce_session,
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
    EcommerceRefreshRequest,
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
from app.services.pessoa_merge_service import executar_fusao_pessoas
from app.services.sales_channel import normalize_online_sales_channel
from app.tenancy.rls import sync_rls_auth_email


router = APIRouter()


def _existing_user_for_phone(db: Session, tenant_id, phone: str) -> User | None:
    """A public signup must not claim a phone already owned by an ERP/app account."""
    digits = _digits_only(phone)
    if len(digits) == 13 and digits.startswith("55"):
        digits = digits[2:]
    stored_phone = User.telefone
    for character in (" ", "+", "-", "(", ")", ".", "/"):
        stored_phone = func.replace(stored_phone, character, "")
    return (
        db.query(User)
        .filter(
            User.tenant_id == tenant_id,
            or_(
                User.login_phone == digits,
                stored_phone == digits,
                stored_phone == f"55{digits}",
            ),
        )
        .order_by(User.is_active.desc(), User.id.desc())
        .first()
    )


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

    existing_phone_user = _existing_user_for_phone(db, tenant_id, telefone)
    if existing_phone_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Este telefone ja possui uma conta nesta loja. Entre com o acesso existente "
                "ou solicite ao ERP a revisao do cadastro."
            ),
        )

    phone_digits = _phone_digits(telefone)
    people = [
        person
        for person in (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.ativo.is_not(False),
                or_(Cliente.telefone.isnot(None), Cliente.celular.isnot(None)),
            )
            .all()
        )
        if phone_digits
        in {_phone_digits(person.telefone), _phone_digits(person.celular)}
        and not person.merged_into_id
    ]
    if any(person.auth_user_id for person in people):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Este telefone ja esta vinculado a uma pessoa com acesso nesta loja. "
                "Entre com a conta existente ou solicite ao ERP a revisao do cadastro."
            ),
        )
    if any(
        person.tipo_cadastro in {"funcionario", "veterinario"} or person.is_entregador
        for person in people
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O acesso desta pessoa deve ser criado e gerenciado pelo ERP.",
        )
    if any(_digits_only(person.cpf) not in {"", cpf_normalizado} for person in people):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este telefone pertence a uma pessoa com CPF diferente. Revise o cadastro no ERP.",
        )
    existing_person = _select_preferred_cliente(
        people,
        email=None,
        cpf=cpf_normalizado,
        telefone=telefone,
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
    db.flush()
    if existing_person:
        cliente = existing_person
        cliente.auth_user_id = user.id
        for duplicate in people:
            if duplicate.id == cliente.id:
                continue
            executar_fusao_pessoas(
                db,
                tenant_id=tenant_id,
                principal_id=cliente.id,
                duplicado_id=duplicate.id,
                decisoes_campos={},
                user_id=user.id,
                observacao="Unificacao por telefone no cadastro publico.",
                modo="ecommerce_cadastro",
                motivo="telefone_e_cpf_compativeis",
                commit=False,
            )
    else:
        cliente = _get_or_create_cliente_for_user(
            db, user, origem_cliente=canal_registro
        )
    if nome:
        cliente.nome = nome
    if cpf_normalizado and not cliente.cpf:
        cliente.cpf = cpf_normalizado
    cliente.telefone = telefone
    _ensure_active_store_access(db, user, str(tenant_id))
    if EMAIL_VERIFICATION_REQUIRED:
        enviado = _send_email_verification(user, canal_registro)
        if not enviado:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Nao foi possivel enviar o e-mail de confirmacao agora. Tente novamente em instantes.",
            )
    register_account_created(db, user, request, canal_registro)
    db.commit()
    db.refresh(user)
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

    auth_payload = _create_ecommerce_session_tokens(db, user, str(tenant_id), request)

    return {
        **auth_payload,
        "user": _serialize_profile(user, cliente, db),
    }


@router.post("/login")
def login_cliente(
    payload: EcommerceLoginRequest, request: Request, db: Session = Depends(get_session)
):
    tenant_id = _extract_tenant_id_from_request(request)
    identifier = str(payload.identifier or "").strip().lower()
    phone_digits = _digits_only(identifier)
    if len(phone_digits) == 13 and phone_digits.startswith("55"):
        phone_digits = phone_digits[2:]
    phone_identifier = phone_digits if len(phone_digits) in {10, 11} else None
    if phone_identifier:
        user = _existing_user_for_phone(db, tenant_id, phone_identifier)
    else:
        user = (
            db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                or_(
                    func.lower(User.email) == identifier,
                    User.username == identifier,
                ),
            )
            .first()
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
            detail="E-mail, celular, usuario ou senha invalidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Conta inativa"
        )

    if user.email and _email_verification_block(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email ainda nao confirmado. Verifique sua caixa de entrada ou solicite um novo link.",
        )

    _ensure_active_store_access(db, user, str(tenant_id))
    register_successful_login(db, user, request)
    db.commit()

    auth_payload = _create_ecommerce_session_tokens(db, user, str(tenant_id), request)

    cliente = _get_or_create_cliente_for_user(db, user)
    db.commit()

    return {
        **auth_payload,
        "user": _serialize_profile(user, cliente, db),
    }


@router.post("/refresh")
def refresh_customer_session(
    payload: EcommerceRefreshRequest,
    request: Request,
    db: Session = Depends(get_session),
):
    return _refresh_ecommerce_session(payload.refresh_token, db, request)
