"""Helpers compartilhados pelas rotas de clientes."""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AppAccessProfile, Cliente, User


def _somente_digitos_coluna(coluna):
    """Normaliza telefone/celular removendo caracteres de mascara para busca numerica."""
    return func.replace(
        func.replace(
            func.replace(
                func.replace(
                    func.replace(
                        func.replace(
                            func.replace(func.coalesce(coluna, ""), "(", ""),
                            ")",
                            "",
                        ),
                        "-",
                        "",
                    ),
                    " ",
                    "",
                ),
                "+",
                "",
            ),
            ".",
            "",
        ),
        "/",
        "",
    )


def _somente_digitos(valor) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _validar_telefone_cliente_obrigatorio(cliente_data, cliente_atual=None) -> None:
    tipo = getattr(cliente_data, "tipo_cadastro", None)
    if tipo is None and cliente_atual is not None:
        tipo = getattr(cliente_atual, "tipo_cadastro", None)

    if tipo and tipo != "cliente":
        return

    telefone = getattr(cliente_data, "telefone", None)
    celular = getattr(cliente_data, "celular", None)
    if telefone is None and cliente_atual is not None:
        telefone = getattr(cliente_atual, "telefone", None)
    if celular is None and cliente_atual is not None:
        celular = getattr(cliente_atual, "celular", None)

    if max(len(_somente_digitos(telefone)), len(_somente_digitos(celular))) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telefone/celular obrigatorio para cadastro de cliente",
        )


def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant."""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_cliente_ou_404(db: Session, cliente_id: int, tenant_id: str):
    """Busca cliente com validacao de tenant e retorna 404 se nao encontrado."""
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
        )

    return cliente


def _anexar_metadados_criacao_cliente(db: Session, clientes):
    lista = clientes if isinstance(clientes, list) else [clientes]
    user_ids = {
        cliente.user_id for cliente in lista if getattr(cliente, "user_id", None)
    }
    usuarios_por_id = {}
    if user_ids:
        usuarios_por_id = {
            usuario.id: usuario
            for usuario in db.query(User).filter(User.id.in_(user_ids)).all()
        }

    auth_user_ids = {
        cliente.auth_user_id
        for cliente in lista
        if getattr(cliente, "auth_user_id", None)
    }
    usuarios_app_por_id = {}
    if auth_user_ids:
        usuarios_app_por_id = {
            usuario.id: usuario
            for usuario in db.query(User).filter(User.id.in_(auth_user_ids)).all()
        }

    cliente_ids = [cliente.id for cliente in lista if getattr(cliente, "id", None)]
    perfis_por_cliente: dict[int, list[str]] = {
        cliente_id: [] for cliente_id in cliente_ids
    }
    if cliente_ids:
        perfis = (
            db.query(AppAccessProfile)
            .filter(
                AppAccessProfile.cliente_id.in_(cliente_ids),
                AppAccessProfile.is_active.is_(True),
            )
            .order_by(AppAccessProfile.id.asc())
            .all()
        )
        for perfil in perfis:
            perfis_por_cliente.setdefault(perfil.cliente_id, []).append(
                perfil.profile_type
            )

    for cliente in lista:
        criado_por_id = getattr(cliente, "user_id", None)
        usuario = usuarios_por_id.get(criado_por_id)
        setattr(cliente, "criado_por_id", criado_por_id)
        setattr(
            cliente,
            "criado_por_nome",
            (getattr(usuario, "nome", None) or getattr(usuario, "email", None))
            if usuario
            else None,
        )
        setattr(
            cliente,
            "criado_por_email",
            getattr(usuario, "email", None) if usuario else None,
        )
        auth_user = usuarios_app_por_id.get(getattr(cliente, "auth_user_id", None))
        setattr(
            cliente,
            "auth_user_nome",
            getattr(auth_user, "nome", None) if auth_user else None,
        )
        setattr(
            cliente,
            "auth_user_email",
            getattr(auth_user, "email", None) if auth_user else None,
        )
        setattr(
            cliente,
            "app_access_profiles",
            perfis_por_cliente.get(getattr(cliente, "id", None), []),
        )
    return clientes


def gerar_codigo_cliente(
    db: Session, tipo_cadastro: str, tipo_pessoa: str, tenant_id: int
) -> str:
    """
    Gera codigo unico e crescente para o cliente neste tenant.
    Pega o maior codigo numerico existente, ativo ou inativo, e soma 1.
    """
    from sqlalchemy import cast as sqcast
    from sqlalchemy import func as sqlfunc
    from sqlalchemy.dialects.postgresql import BIGINT

    resultado = (
        db.query(sqlfunc.max(sqcast(Cliente.codigo, BIGINT)))
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.codigo.op("~")("^[0-9]+$"),
        )
        .scalar()
    )

    proximo = (resultado or 10000) + 1
    return str(proximo)
