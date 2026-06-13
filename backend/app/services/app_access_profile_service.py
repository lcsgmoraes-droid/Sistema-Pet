from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models import AppAccessProfile, Cliente, User


PROFILE_ORDER = ("cliente", "funcionario", "entregador", "veterinario")
PROFILE_LABELS = {
    "cliente": "Cliente",
    "funcionario": "Funcionario",
    "entregador": "Entregador",
    "veterinario": "Veterinario",
}


def normalize_profile_type(value: Any) -> str | None:
    profile_type = str(value or "").strip().casefold()
    if profile_type in PROFILE_ORDER:
        return profile_type
    return None


def _digits_only(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _is_active_cliente(cliente: Any) -> bool:
    return bool(cliente) and getattr(cliente, "ativo", True) is not False


def _profile_dict(profile_type: str, cliente: Any, *, source: str) -> dict[str, Any]:
    return {
        "type": profile_type,
        "label": PROFILE_LABELS[profile_type],
        "cliente_id": getattr(cliente, "id", None),
        "nome": getattr(cliente, "nome", None),
        "source": source,
    }


def _put_profile(
    profiles_by_type: dict[str, dict[str, Any]],
    profile_type: str | None,
    cliente: Any,
    *,
    source: str,
) -> None:
    profile_type = normalize_profile_type(profile_type)
    if not profile_type or not _is_active_cliente(cliente):
        return
    profiles_by_type.setdefault(profile_type, _profile_dict(profile_type, cliente, source=source))


def build_available_profiles_for_clientes(
    user: Any,
    clientes: Iterable[Any],
    *,
    explicit_grants: Iterable[Any] | None = None,
) -> list[dict[str, Any]]:
    profiles_by_type: dict[str, dict[str, Any]] = {}
    clientes_by_id: dict[int, Any] = {}

    for cliente in clientes:
        if not _is_active_cliente(cliente):
            continue
        cliente_id = getattr(cliente, "id", None)
        if cliente_id is not None:
            clientes_by_id[int(cliente_id)] = cliente

        tipo_cadastro = str(getattr(cliente, "tipo_cadastro", "") or "").strip().casefold()
        if tipo_cadastro == "cliente":
            _put_profile(profiles_by_type, "cliente", cliente, source="cadastro")
        if tipo_cadastro == "funcionario":
            _put_profile(profiles_by_type, "funcionario", cliente, source="cadastro")
        if tipo_cadastro == "veterinario":
            _put_profile(profiles_by_type, "veterinario", cliente, source="cadastro")
        if bool(getattr(cliente, "is_entregador", False)) and getattr(cliente, "entregador_ativo", True) is not False:
            _put_profile(profiles_by_type, "entregador", cliente, source="cadastro")

    for grant in explicit_grants or []:
        if getattr(grant, "is_active", True) is False:
            continue
        profile_type = normalize_profile_type(getattr(grant, "profile_type", None))
        grant_cliente = getattr(grant, "cliente", None)
        if not grant_cliente:
            grant_cliente_id = getattr(grant, "cliente_id", None)
            if grant_cliente_id is not None:
                grant_cliente = clientes_by_id.get(int(grant_cliente_id))
        _put_profile(profiles_by_type, profile_type, grant_cliente, source="liberado")

    if not profiles_by_type:
        first_active = next((cliente for cliente in clientes if _is_active_cliente(cliente)), None)
        if first_active:
            _put_profile(profiles_by_type, "cliente", first_active, source="padrao")

    return [
        profiles_by_type[profile_type]
        for profile_type in PROFILE_ORDER
        if profile_type in profiles_by_type
    ]


def apply_selected_profile_flags(
    payload: dict[str, Any],
    available_profiles: list[dict[str, Any]],
    selected_profile: str | None,
) -> dict[str, Any]:
    selected_type = normalize_profile_type(selected_profile)
    selected = next(
        (profile for profile in available_profiles if profile["type"] == selected_type),
        None,
    )
    if not selected:
        selected = available_profiles[0] if available_profiles else None

    profile_type = selected["type"] if selected else "cliente"
    cliente_id = selected.get("cliente_id") if selected else payload.get("cliente_id")

    payload.update(
        {
            "cliente_id": cliente_id,
            "is_entregador": profile_type == "entregador",
            "is_funcionario": profile_type == "funcionario",
            "funcionario_id": cliente_id if profile_type in {"entregador", "funcionario"} else None,
            "is_veterinario": profile_type == "veterinario",
            "veterinario_id": cliente_id if profile_type == "veterinario" else None,
            "perfil_operacional": profile_type,
            "selected_profile": profile_type,
            "available_profiles": available_profiles,
        }
    )
    return payload


def _cliente_matches_user(cliente: Cliente, user: User) -> bool:
    email = (getattr(user, "email", None) or "").strip().casefold()
    cpf = _digits_only(getattr(user, "cpf_cnpj", None))
    telefone = _digits_only(getattr(user, "telefone", None))
    if getattr(cliente, "user_id", None) == getattr(user, "id", None):
        return True
    if email and (getattr(cliente, "email", None) or "").strip().casefold() == email:
        return True
    if cpf and _digits_only(getattr(cliente, "cpf", None)) == cpf:
        return True
    if telefone and telefone in {
        _digits_only(getattr(cliente, "telefone", None)),
        _digits_only(getattr(cliente, "celular", None)),
    }:
        return True
    return False


def find_app_profile_clientes_for_user(
    db: Session,
    user: User,
    *,
    include_cliente: Cliente | None = None,
) -> list[Cliente]:
    tenant_id = str(getattr(user, "tenant_id", "") or "")
    clientes: list[Cliente] = []
    seen_ids: set[int] = set()

    def add(cliente: Cliente | None) -> None:
        if not cliente or not _is_active_cliente(cliente):
            return
        cliente_id = int(getattr(cliente, "id", 0) or 0)
        if cliente_id in seen_ids:
            return
        seen_ids.add(cliente_id)
        clientes.append(cliente)

    add(include_cliente)

    query = db.query(Cliente).filter(Cliente.tenant_id == tenant_id, Cliente.ativo == True)
    filters = [Cliente.user_id == user.id]
    email = (getattr(user, "email", None) or "").strip().casefold()
    if email:
        filters.append(func.lower(Cliente.email) == email)
    cpf = getattr(user, "cpf_cnpj", None)
    if cpf:
        filters.append(Cliente.cpf == cpf)
    telefone = getattr(user, "telefone", None)
    if telefone:
        filters.extend([Cliente.telefone == telefone, Cliente.celular == telefone])

    for cliente in query.filter(or_(*filters)).order_by(Cliente.id.asc()).all():
        if _cliente_matches_user(cliente, user):
            add(cliente)

    return clientes


def list_explicit_app_access_profiles(
    db: Session,
    *,
    tenant_id: Any,
    user_id: int,
    cliente_ids: Iterable[int],
) -> list[AppAccessProfile]:
    ids = {int(cliente_id) for cliente_id in cliente_ids if cliente_id is not None}
    filters = [AppAccessProfile.user_id == user_id]
    if ids:
        filters.append(AppAccessProfile.cliente_id.in_(ids))

    try:
        query = db.query(AppAccessProfile)
    except (AttributeError, IndexError):
        return []

    if hasattr(query, "options"):
        query = query.options(joinedload(AppAccessProfile.cliente))

    return (
        query.filter(
            AppAccessProfile.tenant_id == tenant_id,
            AppAccessProfile.is_active == True,
            or_(*filters),
        )
        .order_by(AppAccessProfile.id.asc())
        .all()
    )


def resolve_user_app_profiles(
    db: Session,
    user: User,
    *,
    include_cliente: Cliente | None = None,
) -> list[dict[str, Any]]:
    tenant_id = str(getattr(user, "tenant_id", "") or "")
    clientes = find_app_profile_clientes_for_user(db, user, include_cliente=include_cliente)
    grants = list_explicit_app_access_profiles(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        cliente_ids=[cliente.id for cliente in clientes],
    )
    return build_available_profiles_for_clientes(user, clientes, explicit_grants=grants)


def get_cliente_for_app_profile_or_none(
    db: Session,
    user: User,
    profile_type: str,
) -> Cliente | None:
    normalized = normalize_profile_type(profile_type)
    if not normalized:
        return None

    tenant_id = str(getattr(user, "tenant_id", "") or "")
    clientes = find_app_profile_clientes_for_user(db, user)
    grants = list_explicit_app_access_profiles(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        cliente_ids=[cliente.id for cliente in clientes],
    )
    profiles = build_available_profiles_for_clientes(user, clientes, explicit_grants=grants)
    profile = next((item for item in profiles if item["type"] == normalized), None)
    cliente_id = profile.get("cliente_id") if profile else None
    if not cliente_id:
        return None

    for cliente in clientes:
        if int(getattr(cliente, "id", 0) or 0) == int(cliente_id):
            return cliente

    try:
        query = db.query(Cliente)
    except (AttributeError, IndexError):
        return None

    return (
        query.filter(
            Cliente.tenant_id == tenant_id,
            Cliente.id == cliente_id,
            Cliente.ativo == True,
        )
        .first()
    )


def sync_cliente_app_access_profiles(
    db: Session,
    *,
    tenant_id: Any,
    cliente: Cliente,
    profile_types: Iterable[str],
    granted_by_user_id: int | None = None,
) -> list[str]:
    normalized = {
        profile_type
        for profile_type in (normalize_profile_type(item) for item in profile_types)
        if profile_type
    }

    existing = (
        db.query(AppAccessProfile)
        .filter(
            AppAccessProfile.tenant_id == tenant_id,
            AppAccessProfile.cliente_id == cliente.id,
        )
        .all()
    )
    by_type = {item.profile_type: item for item in existing}

    for profile_type in PROFILE_ORDER:
        item = by_type.get(profile_type)
        should_enable = profile_type in normalized
        if item:
            item.is_active = should_enable
            if should_enable and not item.user_id:
                item.user_id = getattr(cliente, "user_id", None)
        elif should_enable:
            db.add(
                AppAccessProfile(
                    tenant_id=tenant_id,
                    user_id=getattr(cliente, "user_id", None),
                    cliente_id=cliente.id,
                    profile_type=profile_type,
                    is_active=True,
                    granted_by_user_id=granted_by_user_id,
                )
            )

    return [profile_type for profile_type in PROFILE_ORDER if profile_type in normalized]
