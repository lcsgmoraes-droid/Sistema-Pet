"""Helpers compartilhados pelas rotas de clientes."""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AppAccessProfile, Cliente, User, UserTenant


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
    is_cliente = getattr(cliente_data, "is_cliente", None)
    if is_cliente is None and cliente_atual is not None:
        is_cliente = getattr(cliente_atual, "is_cliente", None)

    if not is_cliente:
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


CAMPO_FLAG_POR_TIPO_CADASTRO = {
    "cliente": "is_cliente",
    "fornecedor": "is_fornecedor",
    "veterinario": "is_veterinario",
    "funcionario": "is_funcionario",
}


def tipos_cadastro_da_pessoa(pessoa) -> list[str]:
    """Lista de tipos marcados (['cliente', 'funcionario'] etc.) a partir das flags."""
    return [
        tipo
        for tipo, campo in CAMPO_FLAG_POR_TIPO_CADASTRO.items()
        if bool(getattr(pessoa, campo, False))
    ]


_MSG_TIPO_OBRIGATORIO = "Selecione ao menos um tipo de cadastro (cliente, fornecedor, veterinário ou funcionário)."


def _validar_flags_tipo_criacao(cliente_data) -> None:
    if not any(getattr(cliente_data, campo) for campo in CAMPO_FLAG_POR_TIPO_CADASTRO.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=_MSG_TIPO_OBRIGATORIO
        )


def _validar_flags_tipo_update(cliente_data, cliente_atual) -> None:
    campos_flag = tuple(CAMPO_FLAG_POR_TIPO_CADASTRO.values())
    if not any(getattr(cliente_data, campo) is not None for campo in campos_flag):
        return

    def efetivo(campo):
        valor = getattr(cliente_data, campo)
        return valor if valor is not None else getattr(cliente_atual, campo)

    if not any(efetivo(campo) for campo in campos_flag):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=_MSG_TIPO_OBRIGATORIO
        )


def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant."""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_cliente_ou_404(db: Session, cliente_id: int, tenant_id: str):
    """Busca cadastro de pessoa visivel para a loja: a propria ou, por grupo comercial, as demais do grupo."""
    from sqlalchemy import or_

    from app.tenancy.filters import pessoa_visivel_no_grupo

    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id,
            or_(Cliente.tenant_id == tenant_id, pessoa_visivel_no_grupo(Cliente, tenant_id)),
        )
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
    liberacao_crediario_por_conta = {}
    if auth_user_ids:
        usuarios_app_por_id = {
            usuario.id: usuario
            for usuario in db.query(User).filter(User.id.in_(auth_user_ids)).all()
        }
        liberacao_crediario_por_conta = {
            (str(vinculo.tenant_id), vinculo.user_id): bool(
                vinculo.pode_liberar_venda_crediario_atrasado
            )
            for vinculo in db.query(UserTenant)
            .filter(UserTenant.user_id.in_(auth_user_ids))
            .all()
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
            "auth_user_username",
            getattr(auth_user, "username", None) if auth_user else None,
        )
        setattr(
            cliente,
            "app_access_profiles",
            perfis_por_cliente.get(getattr(cliente, "id", None), []),
        )
        setattr(
            cliente,
            "pode_liberar_venda_crediario_atrasado",
            liberacao_crediario_por_conta.get(
                (str(cliente.tenant_id), cliente.auth_user_id), False
            ),
        )
    return clientes


def gerar_codigo_cliente(db: Session, tipo_pessoa: str, tenant_id: int) -> str:
    """
    Gera codigo unico e crescente para o cadastro de pessoa dentro do grupo comercial.
    Pega o maior codigo numerico existente entre as lojas do grupo, e soma 1.
    """
    from sqlalchemy import cast as sqcast
    from sqlalchemy import func as sqlfunc
    from sqlalchemy.dialects.postgresql import BIGINT

    from app.services.grupo_codigos import ids_uuid_do_grupo, trava_codigos_do_grupo

    trava_codigos_do_grupo(db, tenant_id, "codigo_pessoa")
    resultado = (
        db.query(sqlfunc.max(sqcast(Cliente.codigo, BIGINT)))
        .filter(
            Cliente.tenant_id.in_(ids_uuid_do_grupo(db, tenant_id)),
            Cliente.codigo.op("~")("^[0-9]+$"),
        )
        .scalar()
    )

    proximo = (resultado or 10000) + 1
    return str(proximo)
