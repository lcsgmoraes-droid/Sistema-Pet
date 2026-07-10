from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.models import Cliente, User
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
    _create_ecommerce_token_pair,
    _ecommerce_auth_payload,
    _get_current_ecommerce_user,
    _session_expiry_utc,
    security,
)
from app.routes.ecommerce_auth_schemas import (
    EcommerceProfileUpdateRequest,
    EcommerceSelectProfileRequest,
)
from app.services.app_access_profile_service import (
    apply_selected_profile_flags,
    build_available_profiles_for_clientes,
    normalize_profile_type,
    resolve_user_app_profiles,
)
from app.security.jwt_compat import JWTError, jwt
from app.session_manager import get_session_by_jti


router = APIRouter()


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
        "funcionario_id": cliente.id
        if (cliente and (is_entregador or is_funcionario))
        else None,
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
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
    db_session = get_session_by_jti(db, token_jti) if token_jti else None
    if not db_session or db_session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao invalida. Faca login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, refresh_token = _create_ecommerce_token_pair(
        user=current_user,
        token_jti=token_jti,
        expires_at=_session_expiry_utc(db_session),
        tenant_id=str(current_user.tenant_id),
        active_profile=profile_type,
    )

    return {
        **_ecommerce_auth_payload(access_token, refresh_token),
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
