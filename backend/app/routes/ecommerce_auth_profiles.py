from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.db import get_session
from app.models import (
    AppAccessProfile,
    AppNotification,
    Cliente,
    User,
    UserPushDevice,
    UserSession,
    UserTenant,
)
from app.pedido_models import Pedido, PedidoItem
from app.routes.ecommerce_auth_cliente import (
    _copy_missing_cliente_fields,
    _digits_only,
    _extract_ecommerce_delivery_details,
    _find_cliente_match,
    _get_or_create_cliente_for_user,
    _select_preferred_cliente,
    _transfer_cliente_relations_for_ecommerce_merge,
    _upsert_delivery_details,
)
from app.routes.ecommerce_auth_common import (
    _activate_user_tenant_context,
    _get_current_ecommerce_user,
)
from app.routes.ecommerce_auth_schemas import (
    EcommerceAccountDeletionRequest,
    EcommerceProfileUpdateRequest,
    EcommerceSelectProfileRequest,
)
from app.services.app_access_profile_service import (
    apply_selected_profile_flags,
    build_available_profiles_for_clientes,
    normalize_profile_type,
    resolve_user_app_profiles,
)
from app.services.lgpd_service import PrivacyOpsService, utcnow

router = APIRouter()


def _anonymize_ecommerce_user(user: User, *, now: datetime) -> None:
    user.email = (
        f"conta-excluida-{user.id}-{secrets.token_hex(8)}@deleted.corepet.invalid"
    )
    user.hashed_password = hash_password(secrets.token_urlsafe(48))
    user.is_active = False
    user.is_admin = False
    user.nome = None
    user.telefone = None
    user.cpf_cnpj = None
    user.foto_url = None
    user.push_token = None
    user.vet_calendar_token = None
    user.consent_date = None
    user.consent_version = None
    user.privacy_version = None
    user.consent_ip = None
    user.consent_user_agent = None
    user.email_verified = False
    user.email_verified_at = None
    user.email_verification_token_hash = None
    user.email_verification_token_expires = None
    user.email_verification_sent_at = None
    user.two_factor_enabled = False
    user.two_factor_secret = None
    user.backup_codes = None
    user.reset_token = None
    user.reset_token_expires = None
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = None
    user.last_login_ip = None
    user.password_changed_at = now
    user.oauth_provider = None
    user.oauth_id = None
    user.nome_loja = None
    user.endereco_loja = None
    user.telefone_loja = None


def _serialize_profile(
    user: User,
    cliente: Cliente | None,
    db: Session | None = None,
    selected_profile: str | None = None,
) -> dict:
    delivery = _extract_ecommerce_delivery_details(cliente)
    if db is not None:
        available_profiles = resolve_user_app_profiles(
            db, user, include_cliente=cliente
        )
    else:
        available_profiles = build_available_profiles_for_clientes(
            user, [cliente] if cliente else []
        )
    is_entregador = bool(getattr(cliente, "is_entregador", False)) if cliente else False
    is_veterinario = bool(
        cliente
        and getattr(cliente, "tipo_cadastro", None) == "veterinario"
        and getattr(cliente, "ativo", True) is not False
    )
    is_funcionario = bool(
        cliente
        and getattr(cliente, "tipo_cadastro", None) == "funcionario"
        and getattr(cliente, "ativo", True) is not False
    )
    if is_veterinario:
        perfil_operacional = "veterinario"
    elif is_entregador:
        perfil_operacional = "entregador"
    elif is_funcionario:
        perfil_operacional = "funcionario"
    else:
        perfil_operacional = "cliente"
    payload = {
        "id": user.id,
        "email": user.email,
        "email_verified": user.email_verified,
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
        "usar_endereco_entrega_diferente": delivery.get(
            "usar_endereco_entrega_diferente", False
        ),
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
        "is_entregador": is_entregador,
        "is_funcionario": is_funcionario,
        "funcionario_id": (
            cliente.id if (cliente and (is_entregador or is_funcionario)) else None
        ),
        "is_veterinario": is_veterinario,
        "veterinario_id": cliente.id if (cliente and is_veterinario) else None,
        "perfil_operacional": perfil_operacional,
        "selected_profile": perfil_operacional,
        "available_profiles": available_profiles,
    }
    return apply_selected_profile_flags(
        payload, available_profiles, selected_profile or perfil_operacional
    )


@router.get("/me")
def me(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    tenant_id = _activate_user_tenant_context(current_user)
    cliente = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.user_id == current_user.id)
        .first()
    )
    data = _serialize_profile(
        current_user,
        cliente,
        db,
        selected_profile=getattr(current_user, "_active_app_profile", None),
    )
    data["is_active"] = current_user.is_active
    return data


@router.get("/perfil")
def obter_perfil(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    cliente = _get_or_create_cliente_for_user(db, current_user)
    db.commit()
    return _serialize_profile(
        current_user,
        cliente,
        db,
        selected_profile=getattr(current_user, "_active_app_profile", None),
    )


@router.post("/select-profile")
def selecionar_perfil_app(
    payload: EcommerceSelectProfileRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    profile_type = normalize_profile_type(payload.profile_type)
    if not profile_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Perfil de app invalido"
        )

    cliente = _get_or_create_cliente_for_user(db, current_user)
    db.commit()
    db.refresh(cliente)

    available_profiles = resolve_user_app_profiles(
        db, current_user, include_cliente=cliente
    )
    if profile_type not in {profile["type"] for profile in available_profiles}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Perfil de app nao liberado"
        )

    access_token = create_access_token(
        data={
            "sub": str(current_user.id),
            "email": current_user.email,
            "token_type": "ecommerce_customer",
            "active_profile": profile_type,
        },
        tenant_id=str(current_user.tenant_id),
        role="customer",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _serialize_profile(
            current_user, cliente, db, selected_profile=profile_type
        ),
    }


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nome completo obrigatório"
        )
    if nome_informado and nome_informado != nome_atual and " " not in nome_final:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe nome completo (nome e sobrenome)",
        )

    current_user.nome = nome_final
    cliente.nome = nome_final

    if payload.telefone is not None:
        telefone = payload.telefone.strip()
        if len(_digits_only(telefone)) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone obrigatorio"
            )
        current_user.telefone = telefone or None
        cliente.telefone = telefone or None
    elif len(_digits_only(current_user.telefone or cliente.telefone)) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone obrigatorio"
        )

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
        canonical_cliente = (
            _select_preferred_cliente(
                [cliente, potential_match],
                email=current_user.email,
                cpf=current_user.cpf_cnpj,
                telefone=current_user.telefone,
                prefer_operational=True,
            )
            or cliente
        )
        previous_cliente = (
            potential_match if canonical_cliente.id == cliente.id else cliente
        )

        _copy_missing_cliente_fields(canonical_cliente, previous_cliente)
        canonical_cliente.user_id = current_user.id
        canonical_cliente.ativo = True
        _transfer_cliente_relations_for_ecommerce_merge(
            db, previous_cliente, canonical_cliente
        )
        cliente = canonical_cliente
        previous_cliente.ativo = False
        nota_fusao = (
            f"\n[{datetime.utcnow().isoformat()}] Cadastro e-commerce duplicado #{previous_cliente.id} "
            f"mantido inativo apos fusao no cliente #{cliente.id}."
        )
        previous_cliente.observacoes = (previous_cliente.observacoes or "") + nota_fusao

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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Informe o nome completo para entrega",
                )
            if (
                not entrega_endereco
                or not entrega_numero
                or not entrega_bairro
                or not entrega_cidade
                or not entrega_estado
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Preencha o endereço de entrega completo",
                )

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
            cliente.endereco_entrega = " | ".join(
                [address_line, *[part for part in tail.split(" | ") if part]]
            )

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
    return _serialize_profile(
        current_user,
        cliente,
        db,
        selected_profile=getattr(current_user, "_active_app_profile", None),
    )


@router.delete("/conta")
def excluir_conta(
    payload: EcommerceAccountDeletionRequest,
    request: Request,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    tenant_id = _activate_user_tenant_context(current_user)
    if not verify_password(payload.password, current_user.hashed_password or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha incorreta",
        )

    clientes = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.user_id == current_user.id,
        )
        .order_by(Cliente.id.asc())
        .all()
    )
    cliente_ids = [cliente.id for cliente in clientes]
    client = getattr(request, "client", None)
    ip_address = getattr(client, "host", None)
    user_agent = request.headers.get("user-agent")
    privacy = PrivacyOpsService(db, tenant_id)
    request_ids: list[int] = []

    for cliente in clientes:
        deletion_request = privacy.create_subject_request(
            subject_type="customer",
            subject_id=str(cliente.id),
            request_type="deletion",
            details="Exclusao definitiva solicitada pelo titular no app CorePet.",
            requester_name=current_user.nome,
            requester_email=current_user.email,
            requester_phone=current_user.telefone,
            channel="app_self_service",
            payload={"immediate": True, "account_user_id": current_user.id},
            created_by_user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        privacy.anonymize_customer_from_request(
            request_id=deletion_request.id,
            processed_by_user_id=current_user.id,
            resolution_notes="Exclusao imediata confirmada com a senha da conta.",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        request_ids.append(deletion_request.id)

    db.query(AppAccessProfile).filter(
        AppAccessProfile.tenant_id == tenant_id,
        AppAccessProfile.user_id == current_user.id,
    ).update({"is_active": False}, synchronize_session=False)
    if cliente_ids:
        db.query(AppAccessProfile).filter(
            AppAccessProfile.tenant_id == tenant_id,
            AppAccessProfile.cliente_id.in_(cliente_ids),
        ).update({"is_active": False}, synchronize_session=False)

    db.query(UserTenant).filter(
        UserTenant.tenant_id == tenant_id,
        UserTenant.user_id == current_user.id,
    ).update({"is_active": False}, synchronize_session=False)
    db.query(UserPushDevice).filter(
        UserPushDevice.tenant_id == tenant_id,
        UserPushDevice.user_id == current_user.id,
    ).delete(synchronize_session=False)
    db.query(AppNotification).filter(
        AppNotification.tenant_id == tenant_id,
        AppNotification.user_id == current_user.id,
    ).delete(synchronize_session=False)
    db.query(UserSession).filter(UserSession.user_id == current_user.id).delete(
        synchronize_session=False
    )

    carrinhos = (
        db.query(Pedido)
        .filter(
            Pedido.tenant_id == tenant_id,
            Pedido.cliente_id == current_user.id,
            Pedido.status == "carrinho",
        )
        .all()
    )
    for carrinho in carrinhos:
        db.query(PedidoItem).filter(
            PedidoItem.tenant_id == tenant_id,
            PedidoItem.pedido_id == carrinho.pedido_id,
        ).delete(synchronize_session=False)
        db.delete(carrinho)

    _anonymize_ecommerce_user(current_user, now=utcnow())
    db.commit()
    return {
        "account_deleted": True,
        "message": "Conta excluida definitivamente.",
        "privacy_request_ids": request_ids,
    }
