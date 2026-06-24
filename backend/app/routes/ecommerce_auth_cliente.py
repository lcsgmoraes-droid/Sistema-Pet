import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Cliente, User
from app.routes.ecommerce_auth_common import _activate_user_tenant_context
from app.services.pessoa_merge_service import transferir_referencias_pessoa


def _digits_only(value: str | None) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _is_operational_cliente(cliente: Cliente | None) -> bool:
    if not cliente or getattr(cliente, "ativo", True) is False:
        return False
    return bool(
        getattr(cliente, "tipo_cadastro", None) in {"funcionario", "veterinario"}
        or getattr(cliente, "is_entregador", False)
    )


def _cliente_phones_digits(cliente: Cliente) -> set[str]:
    phones = {
        _digits_only(getattr(cliente, "telefone", None)),
        _digits_only(getattr(cliente, "celular", None)),
    }
    return {phone for phone in phones if phone}


def _identity_match_reasons(
    cliente: Cliente,
    *,
    email: str,
    cpf_digits: str,
    telefone_digits: str,
) -> set[str]:
    reasons: set[str] = set()
    if cpf_digits and _digits_only(getattr(cliente, "cpf", None)) == cpf_digits:
        reasons.add("cpf")
    if email and (getattr(cliente, "email", None) or "").strip().lower() == email:
        reasons.add("email")
    if telefone_digits and telefone_digits in _cliente_phones_digits(cliente):
        reasons.add("telefone")
    return reasons


def _identity_matches_cliente(
    cliente: Cliente,
    *,
    email: str,
    cpf_digits: str,
    telefone_digits: str,
) -> bool:
    return bool(
        _identity_match_reasons(
            cliente,
            email=email,
            cpf_digits=cpf_digits,
            telefone_digits=telefone_digits,
        )
    )


def _codigo_sort_value(cliente: Cliente) -> tuple[int, int | str]:
    codigo = str(getattr(cliente, "codigo", "") or "").strip()
    if codigo.isdigit():
        return (0, int(codigo))
    if codigo:
        return (1, codigo)
    return (2, "")


def _select_preferred_cliente(
    candidates: list[Cliente],
    *,
    email: str | None,
    cpf: str | None,
    telefone: str | None,
    prefer_operational: bool = False,
) -> Cliente | None:
    email_normalized = (email or "").strip().lower()
    cpf_digits = _digits_only(cpf)
    telefone_digits = _digits_only(telefone)
    if not email_normalized and not cpf_digits and not telefone_digits:
        return None

    unique_candidates: list[Cliente] = []
    seen_ids: set[int] = set()
    for candidate in candidates:
        candidate_id = getattr(candidate, "id", None)
        if candidate_id is not None and int(candidate_id) in seen_ids:
            continue
        if candidate_id is not None:
            seen_ids.add(int(candidate_id))
        unique_candidates.append(candidate)

    ranked: list[tuple[tuple, Cliente]] = []
    for candidate in unique_candidates:
        reasons = _identity_match_reasons(
            candidate,
            email=email_normalized,
            cpf_digits=cpf_digits,
            telefone_digits=telefone_digits,
        )
        if not reasons:
            continue

        is_operational = _is_operational_cliente(candidate)
        if prefer_operational:
            operational_rank = 0 if is_operational else 1
        else:
            operational_rank = 1 if is_operational else 0
        active_rank = 0 if getattr(candidate, "ativo", True) is not False else 1
        match_rank = (
            0 if "cpf" in reasons else 1,
            0 if "telefone" in reasons else 1,
            0 if "email" in reasons else 1,
        )
        ranked.append(
            (
                (
                    operational_rank,
                    match_rank,
                    _codigo_sort_value(candidate),
                    active_rank,
                    int(getattr(candidate, "id", 0) or 0),
                ),
                candidate,
            )
        )

    if not ranked:
        return None

    ranked.sort(key=lambda item: item[0])
    return ranked[0][1]


def _select_linked_cliente_fallback(clientes: list[Cliente]) -> Cliente | None:
    if not clientes:
        return None
    active = [
        cliente for cliente in clientes if getattr(cliente, "ativo", True) is not False
    ]
    pool = active or clientes
    return sorted(
        pool,
        key=lambda cliente: (
            _codigo_sort_value(cliente),
            int(getattr(cliente, "id", 0) or 0),
        ),
    )[0]


def _copy_missing_cliente_fields(target: Cliente, source: Cliente) -> None:
    for field_name in (
        "nome",
        "email",
        "telefone",
        "celular",
        "cpf",
        "endereco",
        "cep",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "estado",
        "endereco_entrega",
        "endereco_entrega_2",
        "enderecos_adicionais",
    ):
        if not getattr(target, field_name, None) and getattr(source, field_name, None):
            setattr(target, field_name, getattr(source, field_name))


def _find_operational_cliente_match(
    db: Session,
    *,
    tenant_id: str,
    user: User,
) -> Cliente | None:
    email = (getattr(user, "email", None) or "").strip().lower()
    cpf_digits = _digits_only(getattr(user, "cpf_cnpj", None))
    telefone_digits = _digits_only(getattr(user, "telefone", None))
    if not email and not cpf_digits and not telefone_digits:
        return None

    candidatos = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.ativo.is_(True),
            or_(
                Cliente.tipo_cadastro.in_(["funcionario", "veterinario"]),
                Cliente.is_entregador.is_(True),
            ),
        )
        .order_by(Cliente.id.asc())
        .all()
    )

    for candidato in candidatos:
        if _identity_matches_cliente(
            candidato,
            email=email,
            cpf_digits=cpf_digits,
            telefone_digits=telefone_digits,
        ):
            return candidato

    return None


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
        linked_query = linked_query.filter(Cliente.id != exclude_cliente_id)
        base_query = base_query.filter(Cliente.id != exclude_cliente_id)

    candidates: list[Cliente] = []
    candidates.extend(linked_query.all())

    cpf_digits = _digits_only(cpf)
    if cpf_digits:
        candidates.extend(base_query.filter(Cliente.cpf.isnot(None)).all())

    email = (email or "").strip().lower()
    if email:
        candidates.extend(base_query.filter(Cliente.email == email).all())

    telefone_digits = _digits_only(telefone)
    if telefone_digits:
        candidates.extend(
            base_query.filter(
                or_(
                    Cliente.telefone.isnot(None),
                    Cliente.celular.isnot(None),
                )
            ).all()
        )

    return _select_preferred_cliente(
        candidates,
        email=email,
        cpf=cpf,
        telefone=telefone,
    )


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
        items = [
            item
            for item in current
            if not (isinstance(item, dict) and item.get("tipo") == "ecommerce_entrega")
        ]

    if enabled:
        items.append({"tipo": "ecommerce_entrega", **details})
        cliente.enderecos_adicionais = items
    else:
        cliente.enderecos_adicionais = items if items else None


_CLIENTE_RELATIONSHIPS_TO_TRANSFER = (
    "pets",
    "pendencias_estoque",
    "vendas",
    "contas_receber",
)


def _transfer_cliente_relations_for_ecommerce_merge(
    db: Session,
    previous_cliente: Cliente | None,
    target_cliente: Cliente | None,
) -> int:
    if (
        not previous_cliente
        or not target_cliente
        or previous_cliente.id == target_cliente.id
    ):
        return 0

    transferencias = transferir_referencias_pessoa(
        db,
        tenant_id=getattr(target_cliente, "tenant_id", None)
        or getattr(previous_cliente, "tenant_id", None),
        principal_id=target_cliente.id,
        duplicado_id=previous_cliente.id,
    )
    transferred = int(
        transferencias.get("transferidos_especiais", {}).get("produto_fornecedores")
        or 0
    )
    transferred += sum(
        int(item.get("total") or 0)
        for item in transferencias.get("transferidos_genericos", [])
    )

    db.flush()

    for relationship_name in _CLIENTE_RELATIONSHIPS_TO_TRANSFER:
        try:
            db.expire(previous_cliente, [relationship_name])
        except Exception:
            pass

    return transferred


def _get_or_create_cliente_for_user(db: Session, user: User) -> Cliente:
    tenant_id = _activate_user_tenant_context(user)
    clientes_vinculados = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.user_id == user.id)
        .order_by(Cliente.id.asc())
        .all()
    )

    cliente: Cliente | None = None
    cpf_usuario = getattr(user, "cpf_cnpj", None)
    email_usuario = (getattr(user, "email", None) or "").strip().lower()
    telefone_usuario = getattr(user, "telefone", None)
    cliente_operacional = _find_operational_cliente_match(
        db, tenant_id=tenant_id, user=user
    )
    if cliente_operacional:
        cliente = cliente_operacional

    if clientes_vinculados:
        if not cliente:
            cliente = _select_preferred_cliente(
                clientes_vinculados,
                email=email_usuario,
                cpf=cpf_usuario,
                telefone=telefone_usuario,
                prefer_operational=True,
            )
        if not cliente:
            cliente = _select_linked_cliente_fallback(clientes_vinculados)

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
        if getattr(cliente, "ativo", True) is False:
            cliente.ativo = True
        if not cliente.nome:
            cliente.nome = user.nome or user.email
        if not cliente.email:
            cliente.email = user.email
        if not cliente.telefone and user.telefone:
            cliente.telefone = user.telefone
        if not cliente.cpf and user.cpf_cnpj:
            cliente.cpf = user.cpf_cnpj

    return cliente
