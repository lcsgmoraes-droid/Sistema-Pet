from datetime import datetime, timedelta, timezone
from uuid import UUID
import secrets
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.models import Cliente, User


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


class EcommerceResetPasswordRequest(BaseModel):
    token: str
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


def _extract_tenant_id_from_request(request: Request) -> UUID:
    tenant_id = _normalize_tenant_uuid(request.headers.get("X-Tenant-ID"))
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID obrigatório e deve ser UUID válido",
        )
    return tenant_id


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

    cpf = (cpf or "").strip()
    if cpf:
        linked_by_cpf = linked_query.filter(Cliente.cpf == cpf).first()
        if linked_by_cpf:
            return linked_by_cpf

        matched_by_cpf = base_query.filter(Cliente.cpf == cpf).first()
        if matched_by_cpf:
            return matched_by_cpf

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
    }


@router.post("/registrar")
def registrar_cliente(payload: EcommerceRegisterRequest, request: Request, db: Session = Depends(get_session)):
    tenant_id = _extract_tenant_id_from_request(request)

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        nome=payload.nome,
        is_active=True,
        is_admin=False,
        consent_date=datetime.now(timezone.utc),
        tenant_id=tenant_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    cliente = _get_or_create_cliente_for_user(db, user)
    if payload.nome:
        cliente.nome = payload.nome
    if payload.cpf:
        cpf_clean = payload.cpf.strip()
        if cpf_clean:
            user.cpf_cnpj = cpf_clean
            cliente.cpf = cpf_clean
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

    user = (
        db.query(User)
        .filter(User.email == payload.email, User.tenant_id == tenant_id)
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

    user = (
        db.query(User)
        .filter(User.email == payload.email, User.tenant_id == tenant_id)
        .first()
    )

    if user and user.is_active:
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_MINUTES)
        db.commit()
        return {
            "message": "Se o email existir, enviaremos instruções de recuperação.",
            "reset_token": reset_token,
            "expires_in_minutes": RESET_TOKEN_MINUTES,
        }

    return {"message": "Se o email existir, enviaremos instruções de recuperação."}


@router.post("/resetar-senha")
def resetar_senha(payload: EcommerceResetPasswordRequest, db: Session = Depends(get_session)):
    user = db.query(User).filter(User.reset_token == payload.token).first()

    if not user or not user.reset_token_expires:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido")

    if user.reset_token_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expirado")

    user.hashed_password = hash_password(payload.nova_senha)
    user.reset_token = None
    user.reset_token_expires = None
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

    nome_final = (payload.nome or current_user.nome or "").strip()
    if not nome_final:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome completo obrigatório")
    if " " not in nome_final:
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
        expirado = c.valid_until and c.valid_until < now
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
        LoyaltyStamp,
    )

    cliente = _get_or_create_cliente_for_user(db, current_user)
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    # --- Cashback ---
    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
        )
        .scalar()
    )
    saldo_cashback = float(saldo_raw or 0)

    # --- Carimbos ---
    total_carimbos = (
        db.query(LoyaltyStamp)
        .filter(
            LoyaltyStamp.tenant_id == tenant_id,
            LoyaltyStamp.customer_id == cliente.id,
            LoyaltyStamp.voided_at.is_(None),
        )
        .count()
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
    carimbos_no_cartao = total_carimbos % stamps_to_complete if stamps_to_complete > 0 else 0

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
        "gold_min_spent": float(rp.get("gold_min_spent", 1000)),
        "gold_min_purchases": int(rp.get("gold_min_purchases", 10)),
        "diamond_min_spent": float(rp.get("diamond_min_spent", 3000)),
        "diamond_min_purchases": int(rp.get("diamond_min_purchases", 20)),
        "platinum_min_spent": float(rp.get("platinum_min_spent", 8000)),
        "platinum_min_purchases": int(rp.get("platinum_min_purchases", 40)),
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
        expirado = bool(c.valid_until and c.valid_until < now)
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
            "total_geral": total_carimbos,
            "carimbos_no_cartao": carimbos_no_cartao,
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

