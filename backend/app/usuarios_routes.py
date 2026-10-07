import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, model_validator

from app.db import get_session
from app.auth import get_current_user_and_tenant
from app.auth.core import hash_password
from app.auth.auth_multitenant_support import (
    RESET_TOKEN_MINUTES,
    _build_password_reset_email,
    _issue_password_reset_tokens,
    _resolve_frontend_base_url,
)
from app.security.permissions_decorator import require_permission
from app.clientes.common import gerar_codigo_cliente
from app.models import (
    AppAccessProfile,
    Cliente,
    Role,
    User,
    UserPushDevice,
    UserSession,
    UserTenant,
)
from app.routes.ecommerce_auth_cliente import _digits_only, _phone_digits
from app.routes.ecommerce_auth_profiles import _anonymize_ecommerce_user
from app.usuario_menu_favoritos_models import UsuarioMenuFavorito
from app.clientes.common import gerar_codigo_cliente, tipos_cadastro_da_pessoa
from app.services.app_access_profile_service import sync_cliente_app_access_profiles
from app.services.business_audit_service import (
    build_user_access_metadata,
    log_business_event,
)
from app.services.email_service import send_email
from app.services.auth_security import (
    register_password_changed,
    register_password_reset_requested,
)
from app.services.pessoa_merge_service import executar_fusao_pessoas
from app.security.crediario_override import definir_liberacao_crediario
from app.services.user_account_service import (
    UserAccountError,
    create_tenant_user_account,
    email_exists_globally,
    is_unique_email_violation,
    is_unique_login_phone_violation,
    is_unique_username_violation,
    login_phone_exists_globally,
    normalize_login_phone,
    normalize_username,
    username_exists_in_tenant,
    validate_password,
)
from app.services.user_loja_vinculo_service import (
    VinculoLojaError,
    desvincular_usuario_de_loja,
    listar_lojas_do_grupo_com_vinculo,
    vincular_usuario_a_loja_do_grupo,
    vincular_usuario_a_qualquer_loja_do_grupo,
)
from app.session_manager import revoke_all_sessions
from app.tenancy.rls import sync_rls_auth_user

router = APIRouter(prefix="/usuarios", tags=["Usuários"])
MAX_MENU_FAVORITOS = 8


class LojaAdicionalVinculo(BaseModel):
    tenant_id: str


class UserCreate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None
    login_phone: str | None = Field(default=None, max_length=25)
    nome: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    role_id: int  # Role a ser vinculada ao usuário
    # Pessoa (Cliente) já existente para vincular a este login, encontrada via
    # /clientes/verificar-duplicata/campo. Se None, uma Pessoa nova é criada.
    pessoa_id: int | None = None
    # Perfis de app (cliente/funcionario/veterinario/etc.) para a Pessoa
    # vinculada ou recém-criada — ver app_access_profile_service.
    app_access_profiles: list[str] = Field(default_factory=list)
    # PF/PJ — usado só ao criar uma Pessoa nova (pessoa_id=None). Ignorado ao
    # vincular a uma pessoa já existente, que já tem seu próprio tipo_pessoa.
    tipo_pessoa: str = "PF"
    # Este celular também é WhatsApp? Vai para Cliente.celular_whatsapp — só ao
    # criar Pessoa nova, mesma regra do tipo_pessoa.
    celular_whatsapp: bool = False
    # Outras lojas do mesmo grupo comercial que este usuário também deve
    # acessar (opcional) — ver user_loja_vinculo_service.py. Nunca vincula a
    # loja de fora do grupo comercial da loja atual.
    lojas_adicionais: list[LojaAdicionalVinculo] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.username and not self.email and not self.login_phone:
            raise ValueError("Informe o celular, nome de usuario ou e-mail")
        if not self.nome or not self.nome.strip():
            raise ValueError("Informe o nome da pessoa")
        if not self.app_access_profiles:
            raise ValueError("Selecione ao menos um perfil de acesso")
        if self.tipo_pessoa not in ("PF", "PJ"):
            raise ValueError("tipo_pessoa deve ser PF ou PJ")
        return self


class UsuarioListResponse(BaseModel):
    user_id: int
    username: str | None = None
    email: str | None = None
    login_phone: str | None = None
    nome: str | None = None
    role_id: int
    role: str
    is_active: bool
    pode_liberar_venda_crediario_atrasado: bool = False
    pessoa_id: int | None = None
    pessoa_codigo: str | None = None
    pessoa_nome: str | None = None
    pessoa_tipos_cadastro: list[str] = []

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    username: str | None = None
    email: str | None = None
    login_phone: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class MenuFavoritoItem(BaseModel):
    path: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=120)
    icon_key: str | None = Field(default=None, max_length=80)


class MenuFavoritosPayload(BaseModel):
    items: list[MenuFavoritoItem] = Field(default_factory=list)


class UserCredentialsUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    login_phone: str | None = Field(default=None, max_length=25)
    new_password: str | None = Field(default=None, min_length=8, max_length=72)
    generate_password: bool = False
    role_id: int | None = None

    @model_validator(mode="after")
    def validate_change(self):
        if (
            self.username is None
            and self.login_phone is None
            and self.new_password is None
            and not self.generate_password
            and self.role_id is None
        ):
            raise ValueError(
                "Informe o celular, nome de usuario, uma nova senha ou um perfil"
            )
        if self.new_password is not None and self.generate_password:
            raise ValueError("Escolha uma senha ou gere uma senha, nao as duas opcoes")
        return self


class UserDelete(BaseModel):
    confirmacao: Literal["EXCLUIR"]


class LiberacaoCrediarioUpdate(BaseModel):
    autorizado: bool


def _serializar_menu_favorito(favorito: UsuarioMenuFavorito) -> dict:
    return {
        "path": favorito.path,
        "label": favorito.label,
        "icon_key": favorito.icon_key,
    }


def _normalizar_menu_favoritos(items: list[MenuFavoritoItem]) -> list[MenuFavoritoItem]:
    normalizados: list[MenuFavoritoItem] = []
    vistos: set[str] = set()
    for item in items:
        path = item.path.strip()
        label = item.label.strip()
        icon_key = item.icon_key.strip() if item.icon_key else None
        if not path or not label:
            raise HTTPException(
                status_code=400,
                detail="Favorito precisa ter caminho e nome.",
            )
        if path in vistos:
            continue
        vistos.add(path)
        normalizados.append(MenuFavoritoItem(path=path, label=label, icon_key=icon_key))
    return normalizados


@router.get("/me/menu-favoritos")
def listar_meus_menu_favoritos(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    favoritos = (
        db.query(UsuarioMenuFavorito)
        .filter(
            UsuarioMenuFavorito.tenant_id == tenant_id,
            UsuarioMenuFavorito.user_id == current_user.id,
        )
        .order_by(UsuarioMenuFavorito.position.asc(), UsuarioMenuFavorito.id.asc())
        .all()
    )
    return {"items": [_serializar_menu_favorito(favorito) for favorito in favoritos]}


@router.put("/me/menu-favoritos")
def salvar_meus_menu_favoritos(
    payload: MenuFavoritosPayload,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    if len(payload.items) > MAX_MENU_FAVORITOS:
        raise HTTPException(
            status_code=400,
            detail=f"Escolha no maximo {MAX_MENU_FAVORITOS} favoritos.",
        )

    current_user, tenant_id = user_and_tenant
    favoritos = _normalizar_menu_favoritos(payload.items)
    if len(favoritos) > MAX_MENU_FAVORITOS:
        raise HTTPException(
            status_code=400,
            detail=f"Escolha no maximo {MAX_MENU_FAVORITOS} favoritos.",
        )

    (
        db.query(UsuarioMenuFavorito)
        .filter(
            UsuarioMenuFavorito.tenant_id == tenant_id,
            UsuarioMenuFavorito.user_id == current_user.id,
        )
        .delete(synchronize_session=False)
    )

    for position, item in enumerate(favoritos):
        db.add(
            UsuarioMenuFavorito(
                tenant_id=tenant_id,
                user_id=current_user.id,
                path=item.path,
                label=item.label,
                icon_key=item.icon_key,
                position=position,
            )
        )

    db.commit()
    return {"items": [item.model_dump() for item in favoritos]}


def _email_ja_cadastrado_globalmente(db: Session, email: str) -> bool:
    """Users.email tem unicidade global; a checagem precisa ignorar o filtro de tenant."""
    return email_exists_globally(db, email)


def _vincular_ou_criar_pessoa_para_usuario(
    db: Session,
    *,
    actor: User,
    tenant_id,
    user: User,
    pessoa_id: int | None,
    nome: str | None,
    login_phone: str | None,
    email: str | None,
    tipo_pessoa: str = "PF",
    celular_whatsapp: bool = False,
) -> Cliente:
    """Vincula o novo login a uma Pessoa já existente (encontrada via
    /clientes/verificar-duplicata/campo) ou cria uma Pessoa nova como
    funcionário. Ver .claude/skills/pessoas/SKILL.md."""
    if pessoa_id is not None:
        pessoa = (
            db.query(Cliente)
            .filter(
                Cliente.id == pessoa_id,
                Cliente.tenant_id == tenant_id,
                Cliente.ativo.is_not(False),
            )
            .first()
        )
        if not pessoa:
            raise UserAccountError("Pessoa selecionada não encontrada.", status_code=404)
        if pessoa.auth_user_id is not None and pessoa.auth_user_id != user.id:
            raise UserAccountError(
                "Esta pessoa já está vinculada a outro usuário.", status_code=409
            )
        pessoa.auth_user_id = user.id
        return pessoa

    nome_pessoa = (
        nome or user.nome or user.email or user.username or user.login_phone or f"Usuario {user.id}"
    )
    pessoa = Cliente(
        tenant_id=tenant_id,
        user_id=actor.id,
        auth_user_id=user.id,
        codigo=gerar_codigo_cliente(db, tipo_pessoa, tenant_id),
        tipo_pessoa=tipo_pessoa,
        is_funcionario=True,
        nome=nome_pessoa,
        celular=login_phone,
        celular_whatsapp=celular_whatsapp,
        email=email,
        origem_cliente="cadastro_usuario",
        ativo=True,
    )
    db.add(pessoa)
    db.flush()
    return pessoa


def _is_unique_email_violation(exc: IntegrityError) -> bool:
    return is_unique_email_violation(exc)


def _is_cliente_role(role: Role | None) -> bool:
    return bool(role and (role.name or "").strip().casefold() == "cliente")


def _ensure_role_is_not_cliente(role: Role | None) -> None:
    if _is_cliente_role(role):
        raise UserAccountError(
            "O perfil Cliente e reservado para acesso criado pelo cadastro da pessoa/app. "
            "Para usuario criado direto, selecione um perfil operacional.",
            status_code=400,
        )


def _nome_pessoa_para_usuario(user: User) -> str:
    return (
        (user.nome or "").strip()
        or (user.email or "").strip()
        or (user.username or "").strip()
        or (user.login_phone or "").strip()
        or f"Usuario {user.id}"
    )


def _criar_pessoa_operacional_para_usuario(
    db: Session,
    *,
    actor: User,
    tenant_id,
    user: User,
) -> Cliente:
    pessoa = Cliente(
        tenant_id=tenant_id,
        user_id=actor.id,
        auth_user_id=user.id,
        codigo=gerar_codigo_cliente(db, "PF", tenant_id),
        is_funcionario=True,
        tipo_pessoa="PF",
        nome=_nome_pessoa_para_usuario(user),
        celular=user.login_phone,
        telefone=user.telefone,
        email=user.email,
        origem_cliente="cadastro_usuario",
        ativo=True,
    )
    db.add(pessoa)
    db.flush()
    return pessoa


def _usuario_tem_pessoa_vinculada(db: Session, *, tenant_id, user_id: int) -> bool:
    return (
        db.query(func.count(Cliente.id))
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.auth_user_id == user_id,
            Cliente.ativo.is_not(False),
        )
        .scalar()
        > 0
    )


def _pessoa_operacional_existente(
    db: Session, *, tenant_id, user: User
) -> Cliente | None:
    phone = _phone_digits(user.login_phone or user.telefone)
    if not phone:
        return None
    candidates = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.ativo.is_not(False),
            Cliente.auth_user_id.is_(None),
            or_(Cliente.is_funcionario.is_(True), Cliente.is_veterinario.is_(True)),
        )
        .all()
    )
    matches = [
        person
        for person in candidates
        if phone in {_phone_digits(person.celular), _phone_digits(person.telefone)}
        and (
            not user.cpf_cnpj
            or not person.cpf
            or _digits_only(user.cpf_cnpj) == _digits_only(person.cpf)
        )
    ]
    if len(matches) > 1:
        raise UserAccountError(
            "Ha mais de uma pessoa operacional com este telefone. Funda as fichas em Pessoas antes de alterar o acesso.",
            status_code=409,
        )
    return matches[0] if matches else None


def _vincular_pessoa_operacional_existente(
    db: Session, *, tenant_id, user: User
) -> bool:
    pessoa = _pessoa_operacional_existente(db, tenant_id=tenant_id, user=user)
    if not pessoa:
        return False
    pessoa.auth_user_id = user.id
    return True


def _fundir_pessoa_de_cliente_com_operacional(
    db: Session, *, tenant_id, user: User, actor_user_id: int
) -> bool:
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.auth_user_id == user.id,
            Cliente.ativo.is_not(False),
        )
        .first()
    )
    if not cliente or cliente.is_funcionario or cliente.is_veterinario:
        return False
    if cliente.is_entregador:
        return False
    operacional = _pessoa_operacional_existente(db, tenant_id=tenant_id, user=user)
    if not operacional:
        return False
    try:
        executar_fusao_pessoas(
            db,
            tenant_id=tenant_id,
            principal_id=operacional.id,
            duplicado_id=cliente.id,
            decisoes_campos={},
            user_id=actor_user_id,
            observacao="Consolidacao de pessoa na promocao de acesso pelo ERP.",
            modo="promocao_usuario_erp",
            motivo="telefone_e_cpf_compativeis",
            commit=False,
        )
    except ValueError as exc:
        raise UserAccountError(str(exc), status_code=409) from exc
    return True


@router.get("", response_model=list[UsuarioListResponse])
@require_permission("usuarios.manage")
def listar_usuarios(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista usuários do tenant com informações de role e status"""
    _, tenant_id = user_and_tenant

    rows = (
        db.query(
            User.id.label("user_id"),
            User.username,
            User.email,
            User.login_phone,
            User.nome,
            Role.id.label("role_id"),
            Role.name.label("role"),
            UserTenant.is_active,
            UserTenant.pode_liberar_venda_crediario_atrasado,
            Cliente.id.label("pessoa_id"),
            Cliente.codigo.label("pessoa_codigo"),
            Cliente.nome.label("pessoa_nome"),
            Cliente.is_cliente,
            Cliente.is_fornecedor,
            Cliente.is_veterinario,
            Cliente.is_funcionario,
        )
        .join(UserTenant, UserTenant.user_id == User.id)
        .join(Role, Role.id == UserTenant.role_id)
        .outerjoin(
            Cliente,
            (Cliente.auth_user_id == User.id)
            & (Cliente.tenant_id == tenant_id)
            & (Cliente.ativo.is_not(False)),
        )
        .filter(UserTenant.tenant_id == tenant_id)
        .all()
    )

    return [
        {
            "user_id": row.user_id,
            "username": row.username,
            "email": row.email,
            "login_phone": row.login_phone,
            "nome": row.nome,
            "role_id": row.role_id,
            "role": row.role,
            "is_active": row.is_active,
            "pessoa_id": row.pessoa_id,
            "pessoa_codigo": row.pessoa_codigo,
            "pessoa_nome": row.pessoa_nome,
            "pessoa_tipos_cadastro": tipos_cadastro_da_pessoa(row),
        }
        for row in rows
    ]


@router.patch("/{user_id}/liberacao-crediario")
@require_permission("usuarios.manage")
def atualizar_liberacao_crediario_usuario(
    user_id: int,
    payload: LiberacaoCrediarioUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    actor, tenant_id = user_and_tenant
    definir_liberacao_crediario(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        autorizado=payload.autorizado,
        actor_user_id=actor.id,
    )
    db.commit()
    return {"autorizado": payload.autorizado}


@router.post("", response_model=UserResponse)
@require_permission("usuarios.manage")
def criar_usuario(
    payload: UserCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    actor, tenant_id = user_and_tenant

    try:
        selected_role = (
            db.query(Role)
            .filter(Role.id == payload.role_id, Role.tenant_id == tenant_id)
            .first()
        )
        _ensure_role_is_not_cliente(selected_role)
        user, role = create_tenant_user_account(
            db,
            tenant_id=tenant_id,
            username=payload.username,
            email=payload.email,
            login_phone=payload.login_phone,
            password=payload.password,
            role_id=payload.role_id,
            nome=payload.nome,
        )
        pessoa = _criar_pessoa_operacional_para_usuario(
            db,
            actor=actor,
            tenant_id=tenant_id,
            user=user,
        )
        log_business_event(
            db=db,
            tenant_id=tenant_id,
            user_id=actor.id,
            event="access.user_created",
            entity_type="users",
            entity_id=user.id,
            metadata=build_user_access_metadata(
                actor=actor,
                target_user=user,
                tenant_id=tenant_id,
                role=role,
                extra={"is_active": True, "pessoa_id": pessoa.id},
            ),
            details=f"Usuario #{user.id} criado no tenant",
            commit=False,
        )

        pessoa = _vincular_ou_criar_pessoa_para_usuario(
            db,
            actor=actor,
            tenant_id=tenant_id,
            user=user,
            pessoa_id=payload.pessoa_id,
            nome=payload.nome,
            login_phone=user.login_phone,
            email=payload.email,
            tipo_pessoa=payload.tipo_pessoa,
            celular_whatsapp=payload.celular_whatsapp,
        )
        if payload.app_access_profiles:
            sync_cliente_app_access_profiles(
                db,
                tenant_id=tenant_id,
                cliente=pessoa,
                profile_types=payload.app_access_profiles,
                granted_by_user_id=actor.id,
                linked_user_id=user.id,
            )

        for loja_adicional in payload.lojas_adicionais:
            vincular_usuario_a_loja_do_grupo(
                db,
                usuario=user,
                tenant_origem_id=tenant_id,
                tenant_destino_id=loja_adicional.tenant_id,
                commit=False,
            )

        db.commit()
        db.refresh(user)
    except VinculoLojaError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except UserAccountError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except IntegrityError as exc:
        db.rollback()
        if _is_unique_email_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este e-mail ja esta cadastrado. Use outro e-mail ou verifique se o usuario ja existe em outro tenant.",
            ) from exc
        if is_unique_username_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este nome de usuario ja esta em uso nesta loja.",
            ) from exc
        if is_unique_login_phone_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este celular ja esta vinculado a outro usuario.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nao foi possivel criar o usuario agora. Tente novamente em instantes.",
        ) from exc

    return user


@router.delete("/{user_id}")
@require_permission("usuarios.manage")
def excluir_usuario(
    user_id: int,
    payload: UserDelete,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    actor, tenant_id = user_and_tenant
    if actor.id == user_id:
        raise HTTPException(
            status_code=400, detail="Nao e possivel excluir o proprio acesso."
        )

    row = (
        db.query(User, UserTenant)
        .join(UserTenant, UserTenant.user_id == User.id)
        .filter(
            User.id == user_id,
            User.tenant_id == tenant_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=404, detail="Usuario nao encontrado nesta loja."
        )
    user, vinculo = row

    # O filtro automatico de tenant esconde vinculos de outras lojas. A politica
    # RLS permite que a propria conta veja seus vinculos; restauramos o ator logo apos.
    sync_rls_auth_user(db, user_id)
    try:
        account_tenants = db.execute(
            text("SELECT tenant_id FROM user_tenants WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).all()
    finally:
        sync_rls_auth_user(db, actor.id)
    current_tenant_key = str(tenant_id).replace("-", "")
    tenant_keys = {str(row[0]).replace("-", "") for row in account_tenants}
    if current_tenant_key not in tenant_keys:
        raise HTTPException(
            status_code=409,
            detail="Nao foi possivel confirmar os vinculos desta conta. Tente novamente.",
        )
    if tenant_keys - {current_tenant_key}:
        raise HTTPException(
            status_code=409,
            detail="Esta conta pertence a mais de uma loja. Revise os vinculos antes de excluir.",
        )

    now = datetime.now(timezone.utc)
    linked_people = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.auth_user_id == user_id)
        .all()
    )
    for pessoa in linked_people:
        pessoa.auth_user_id = None

    db.query(AppAccessProfile).filter(
        AppAccessProfile.tenant_id == tenant_id,
        AppAccessProfile.user_id == user_id,
    ).update({"is_active": False}, synchronize_session=False)
    db.query(UserPushDevice).filter(
        UserPushDevice.tenant_id == tenant_id,
        UserPushDevice.user_id == user_id,
    ).delete(synchronize_session=False)
    db.query(UsuarioMenuFavorito).filter(
        UsuarioMenuFavorito.tenant_id == tenant_id,
        UsuarioMenuFavorito.user_id == user_id,
    ).delete(synchronize_session=False)
    db.query(UserSession).filter(UserSession.user_id == user_id).update(
        {
            "revoked": True,
            "revoked_at": now,
            "revoke_reason": "account_removed_by_admin",
        },
        synchronize_session=False,
    )
    db.delete(vinculo)
    _anonymize_ecommerce_user(user, now=now)
    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=actor.id,
        event="access.user_removed",
        entity_type="users",
        entity_id=user_id,
        metadata={
            "actor_user_id": actor.id,
            "target_user_id": user_id,
            "unlinked_people": [pessoa.id for pessoa in linked_people],
        },
        details=f"Acesso do usuario #{user_id} removido em definitivo",
        commit=False,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Nao foi possivel remover esta conta. Revise os vinculos e tente novamente.",
        ) from exc
    return {
        "status": "ok",
        "user_id": user_id,
        "pessoas_desvinculadas": len(linked_people),
    }


@router.patch("/{user_id}/credenciais")
@require_permission("usuarios.manage")
def atualizar_credenciais_usuario(
    user_id: int,
    payload: UserCredentialsUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    actor, tenant_id = user_and_tenant
    row = (
        db.query(User, UserTenant)
        .join(UserTenant, UserTenant.user_id == User.id)
        .filter(
            User.id == user_id,
            User.tenant_id == tenant_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado nesta loja")

    target_user, vinculo = row
    username_changed = False
    login_phone_changed = False
    password_changed = False
    role_changed = False
    selected_role: Role | None = None
    generated_password: str | None = None

    if payload.role_id is not None and target_user.master_grupo_id is not None:
        raise HTTPException(
            status_code=403,
            detail=(
                "Este usuário é o master do grupo comercial — o acesso dele "
                "não pode ser alterado por aqui."
            ),
        )

    try:
        if payload.username is not None:
            normalized_username = normalize_username(payload.username)
            if username_exists_in_tenant(
                db,
                tenant_id=tenant_id,
                username=normalized_username,
                exclude_user_id=target_user.id,
            ):
                raise UserAccountError(
                    "Este nome de usuario ja esta em uso nesta loja.",
                    status_code=409,
                )
            username_changed = target_user.username != normalized_username
            target_user.username = normalized_username

        if payload.login_phone is not None:
            normalized_login_phone = normalize_login_phone(payload.login_phone)
            if login_phone_exists_globally(
                db,
                normalized_login_phone,
                exclude_user_id=target_user.id,
            ):
                raise UserAccountError(
                    "Este celular ja esta vinculado a outro usuario.",
                    status_code=409,
                )
            login_phone_changed = target_user.login_phone != normalized_login_phone
            target_user.login_phone = normalized_login_phone

        new_password = payload.new_password
        if payload.generate_password:
            generated_password = secrets.token_urlsafe(12)
            new_password = generated_password
        if new_password is not None:
            new_password = validate_password(new_password)
            target_user.hashed_password = hash_password(new_password)
            register_password_changed(db, target_user, None, "admin_reset")
            password_changed = True

        if payload.role_id is not None:
            selected_role = (
                db.query(Role)
                .filter(Role.id == payload.role_id, Role.tenant_id == tenant_id)
                .first()
            )
            if not selected_role:
                raise UserAccountError(
                    "Perfil de acesso invalido para esta loja.",
                    status_code=400,
                )
            _ensure_role_is_not_cliente(selected_role)
            role_changed = vinculo.role_id != selected_role.id
            vinculo.role_id = selected_role.id

        if role_changed:
            _fundir_pessoa_de_cliente_com_operacional(
                db, tenant_id=tenant_id, user=target_user, actor_user_id=actor.id
            )

        if not _usuario_tem_pessoa_vinculada(
            db,
            tenant_id=tenant_id,
            user_id=target_user.id,
        ):
            if not _vincular_pessoa_operacional_existente(
                db, tenant_id=tenant_id, user=target_user
            ):
                _criar_pessoa_operacional_para_usuario(
                    db,
                    actor=actor,
                    tenant_id=tenant_id,
                    user=target_user,
                )

        if password_changed or role_changed or login_phone_changed:
            sessions_revoked = revoke_all_sessions(
                db=db,
                user_id=target_user.id,
                reason="admin_access_changed",
            )
        else:
            sessions_revoked = 0

        log_business_event(
            db=db,
            tenant_id=tenant_id,
            user_id=actor.id,
            event="access.user_credentials_changed",
            entity_type="users",
            entity_id=target_user.id,
            metadata=build_user_access_metadata(
                actor=actor,
                target_user=target_user,
                tenant_id=tenant_id,
                role=selected_role,
                extra={
                    "username_changed": username_changed,
                    "login_phone_changed": login_phone_changed,
                    "password_changed": password_changed,
                    "role_changed": role_changed,
                    "sessions_revoked": sessions_revoked,
                },
            ),
            details=f"Credenciais do usuario #{target_user.id} atualizadas",
            commit=True,
        )
    except UserAccountError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except IntegrityError as exc:
        db.rollback()
        if is_unique_username_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este nome de usuario ja esta em uso nesta loja.",
            ) from exc
        if is_unique_login_phone_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este celular ja esta vinculado a outro usuario.",
            ) from exc
        raise

    return {
        "status": "ok",
        "username": target_user.username,
        "login_phone": target_user.login_phone,
        "password_changed": password_changed,
        "role_changed": role_changed,
        "role_id": vinculo.role_id,
        "generated_password": generated_password,
        "sessions_revoked": sessions_revoked,
    }


@router.post("/{user_id}/recriar-senha")
@require_permission("usuarios.manage")
def recriar_senha_usuario(
    user_id: int,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Dispara pro usuario o mesmo processo padrao de "esqueci minha senha"
    (POST /auth/forgot-password) — o admin nunca ve nem define a senha dele,
    so pede pro sistema mandar o link/codigo de recriacao por e-mail. Exige
    e-mail cadastrado (o processo padrao nao tem variante por celular)."""
    actor, tenant_id = user_and_tenant

    user = _usuario_visivel_neste_tenant(db, user_id=user_id, tenant_id=tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if not user.email:
        raise HTTPException(
            status_code=400,
            detail=(
                "Este usuário não tem e-mail cadastrado — não é possível "
                "enviar o link de recriação de senha."
            ),
        )

    reset_code, reset_link_token, stored_reset_token = _issue_password_reset_tokens()
    user.reset_token = stored_reset_token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(
        minutes=RESET_TOKEN_MINUTES
    )

    reset_link = (
        f"{_resolve_frontend_base_url(request)}/recuperar-senha"
        f"?email={quote(user.email)}&token={quote(reset_link_token)}"
    )
    subject, html_body, text_body = _build_password_reset_email(
        user, reset_code, reset_link
    )
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
            status_code=503,
            detail="Não foi possível enviar o e-mail agora. Tente novamente em instantes.",
        )

    register_password_reset_requested(db, user, request)
    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=actor.id,
        event="access.user_password_reset_triggered_by_admin",
        entity_type="users",
        entity_id=user.id,
        metadata={"target_user_id": user.id},
        details=f"Processo de recriacao de senha disparado para {user.email} pelo admin {actor.id}",
        commit=False,
    )
    db.commit()

    return {
        "message": f"E-mail de recriação de senha enviado para {user.email}.",
        "expires_in_minutes": RESET_TOKEN_MINUTES,
    }


class PerfisAppUpdate(BaseModel):
    profiles: list[str] = Field(default_factory=list)


def _obter_pessoa_do_usuario(db: Session, *, user_id: int, tenant_id) -> Cliente:
    pessoa = (
        db.query(Cliente)
        .filter(
            Cliente.auth_user_id == user_id,
            Cliente.tenant_id == tenant_id,
            Cliente.ativo.is_not(False),
        )
        .first()
    )
    if not pessoa:
        raise HTTPException(
            status_code=404,
            detail="Este usuário não tem uma Pessoa vinculada.",
        )
    return pessoa


@router.get("/{user_id}/perfis-app")
@require_permission("usuarios.manage")
def listar_perfis_app_usuario(
    user_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _actor, tenant_id = user_and_tenant
    pessoa = _obter_pessoa_do_usuario(db, user_id=user_id, tenant_id=tenant_id)
    perfis = (
        db.query(AppAccessProfile.profile_type)
        .filter(
            AppAccessProfile.tenant_id == tenant_id,
            AppAccessProfile.cliente_id == pessoa.id,
        )
        .all()
    )
    return {"pessoa_id": pessoa.id, "profiles": [item[0] for item in perfis]}


@router.put("/{user_id}/perfis-app")
@require_permission("usuarios.manage")
def atualizar_perfis_app_usuario(
    user_id: int,
    payload: PerfisAppUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    actor, tenant_id = user_and_tenant
    pessoa = _obter_pessoa_do_usuario(db, user_id=user_id, tenant_id=tenant_id)
    profiles = sync_cliente_app_access_profiles(
        db,
        tenant_id=tenant_id,
        cliente=pessoa,
        profile_types=payload.profiles,
        granted_by_user_id=actor.id,
        linked_user_id=user_id,
    )
    db.commit()
    return {"pessoa_id": pessoa.id, "profiles": profiles}


# ==========================================
# ETAPA B2 — VINCULAR USUÁRIO AO TENANT
# ==========================================


class VinculoCreate(BaseModel):
    role_id: int


class StatusUpdate(BaseModel):
    is_active: bool


@router.post("/{user_id}/vincular")
@require_permission("usuarios.manage")
def vincular_usuario(
    user_id: int,
    payload: VinculoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    actor, tenant_id = user_and_tenant

    user = (
        db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    role = (
        db.query(Role)
        .filter(Role.id == payload.role_id, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=400, detail="Role inválido para este tenant")
    try:
        _ensure_role_is_not_cliente(role)
    except UserAccountError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    existing = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Usuário já vinculado a este tenant"
        )

    vinculo = UserTenant(
        user_id=user_id,
        tenant_id=tenant_id,
        role_id=role.id,
        is_active=True,
    )
    db.add(vinculo)
    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=actor.id,
        event="access.user_linked",
        entity_type="users",
        entity_id=user.id,
        metadata=build_user_access_metadata(
            actor=actor,
            target_user=user,
            tenant_id=tenant_id,
            role=role,
            extra={"is_active": True},
        ),
        details=f"Usuario {user.username or user.email or user.id} vinculado ao tenant",
        commit=False,
    )
    db.commit()

    return {"status": "ok", "message": "Usuário vinculado com sucesso"}


class VinculoLojaCreate(BaseModel):
    tenant_id: str


@router.post("/{user_id}/vincular-loja")
@require_permission("usuarios.manage")
def vincular_usuario_outra_loja(
    user_id: int,
    payload: VinculoLojaCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Vincula um usuário já existente a outra loja do mesmo grupo comercial
    da loja atual (nunca a uma loja de fora do grupo) — ver
    `user_loja_vinculo_service.py`."""
    actor, tenant_id = user_and_tenant

    user = (
        db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    try:
        vincular_usuario_a_loja_do_grupo(
            db,
            usuario=user,
            tenant_origem_id=tenant_id,
            tenant_destino_id=payload.tenant_id,
            commit=False,
        )
    except VinculoLojaError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=actor.id,
        event="access.user_linked_other_store",
        entity_type="users",
        entity_id=user.id,
        metadata={"tenant_destino_id": payload.tenant_id},
        details=f"Usuario {user.username or user.email or user.id} vinculado a outra loja do grupo",
        commit=False,
    )
    db.commit()


def _usuario_visivel_neste_tenant(db: Session, *, user_id: int, tenant_id) -> User | None:
    """Mesmo criterio da listagem (`GET /usuarios`): o usuario aparece aqui
    se tiver um UserTenant pra este tenant, mesmo que a loja "de origem"
    dele (`User.tenant_id`) seja outra — acontece justamente com usuario
    vinculado a mais de uma loja do grupo."""
    vinculo = (
        db.query(UserTenant)
        .filter(UserTenant.user_id == user_id, UserTenant.tenant_id == tenant_id)
        .first()
    )
    if vinculo is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


@router.get("/{user_id}/lojas-grupo")
@require_permission("usuarios.manage")
def listar_lojas_grupo_usuario(
    user_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lojas do mesmo grupo comercial da loja atual, com status de vinculo
    deste usuario em cada uma — base da tela de arrastar-e-soltar."""
    _actor, tenant_id = user_and_tenant

    user = _usuario_visivel_neste_tenant(db, user_id=user_id, tenant_id=tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    lojas = listar_lojas_do_grupo_com_vinculo(
        db, tenant_origem_id=tenant_id, usuario_id=user_id
    )
    return {"lojas": lojas}


@router.post("/{user_id}/lojas-grupo/{tenant_destino_id}")
@require_permission("usuarios.manage")
def vincular_usuario_loja_grupo(
    user_id: int,
    tenant_destino_id: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Vincula o usuario a outra loja do grupo, arrastada pra "associadas" —
    resolve sozinho qual loja ja vinculada usar como origem do perfil de
    acesso (nao precisa ser a loja de quem esta operando a tela)."""
    actor, tenant_id = user_and_tenant

    user = _usuario_visivel_neste_tenant(db, user_id=user_id, tenant_id=tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    try:
        vincular_usuario_a_qualquer_loja_do_grupo(
            db,
            usuario=user,
            tenant_destino_id=tenant_destino_id,
            commit=False,
        )
    except VinculoLojaError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=actor.id,
        event="access.user_linked_other_store",
        entity_type="users",
        entity_id=user.id,
        metadata={"tenant_destino_id": tenant_destino_id},
        details=f"Usuario {user.username or user.email or user.id} vinculado a outra loja do grupo",
        commit=False,
    )
    db.commit()
    return {"status": "ok"}


@router.delete("/{user_id}/lojas-grupo/{tenant_destino_id}")
@require_permission("usuarios.manage")
def desvincular_usuario_loja_grupo(
    user_id: int,
    tenant_destino_id: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Remove o acesso do usuario aquela loja, arrastada pra "disponiveis" —
    nunca deixa o usuario sem nenhuma loja ativa no grupo."""
    actor, tenant_id = user_and_tenant

    user = _usuario_visivel_neste_tenant(db, user_id=user_id, tenant_id=tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    try:
        desvincular_usuario_de_loja(
            db,
            usuario=user,
            tenant_origem_id=tenant_id,
            tenant_destino_id=tenant_destino_id,
            commit=False,
        )
    except VinculoLojaError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=actor.id,
        event="access.user_unlinked_store",
        entity_type="users",
        entity_id=user.id,
        metadata={"tenant_destino_id": tenant_destino_id},
        details=f"Usuario {user.username or user.email or user.id} desvinculado de uma loja do grupo",
        commit=False,
    )
    db.commit()
    return {"status": "ok"}

    return {"status": "ok", "message": "Usuário vinculado à loja com sucesso"}


@router.patch("/{user_id}/status")
@require_permission("usuarios.manage")
def atualizar_status_usuario(
    user_id: int,
    payload: StatusUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    actor, tenant_id = user_and_tenant

    vinculo = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not vinculo:
        raise HTTPException(
            status_code=404, detail="Usuário não vinculado a este tenant"
        )

    if not payload.is_active:
        alvo = db.query(User).filter(User.id == user_id).first()
        if alvo is not None and alvo.master_grupo_id is not None:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Este usuário é o master do grupo comercial — não pode "
                    "ser desativado."
                ),
            )

    previous_status = bool(vinculo.is_active)
    vinculo.is_active = payload.is_active

    sync_rls_auth_user(db, user_id)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if payload.is_active:
            user.is_active = True
        else:
            tem_algum_vinculo_ativo = (
                db.query(UserTenant)
                .filter(
                    UserTenant.user_id == user_id,
                    UserTenant.is_active.is_(True),
                )
                .count()
                > 0
            )
            user.is_active = tem_algum_vinculo_ativo

    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=actor.id,
        event="access.user_status_changed",
        entity_type="users",
        entity_id=user_id,
        old_value={"is_active": previous_status},
        metadata=build_user_access_metadata(
            actor=actor,
            target_user=user,
            tenant_id=tenant_id,
            role=None,
            extra={
                "previous_is_active": previous_status,
                "new_is_active": bool(payload.is_active),
            },
        ),
        details=f"Status de usuario #{user_id} alterado",
        commit=False,
    )
    db.commit()

    return {
        "status": "ok",
        "is_active_vinculo": vinculo.is_active,
        "is_active_usuario": user.is_active if user else None,
    }


@router.post("/{user_id}/forcar-logout")
@require_permission("usuarios.manage")
def forcar_logout_usuario(
    user_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    actor, tenant_id = user_and_tenant

    vinculo = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not vinculo:
        raise HTTPException(
            status_code=404, detail="Usuário não vinculado a este tenant"
        )

    revogadas = revoke_all_sessions(
        db=db,
        user_id=user_id,
        reason="admin_forced_logout",
        tenant_id=tenant_id,
    )

    target_user = db.query(User).filter(User.id == user_id).first()
    log_business_event(
        db=db,
        tenant_id=tenant_id,
        user_id=actor.id,
        event="access.user_forced_logout",
        entity_type="users",
        entity_id=user_id,
        metadata=build_user_access_metadata(
            actor=actor,
            target_user=target_user,
            tenant_id=tenant_id,
            role=None,
            extra={"sessions_revoked": revogadas},
        ),
        details=f"Logout forcado do usuario #{user_id}",
        commit=True,
    )

    return {
        "status": "ok",
        "message": "Logout forçado executado com sucesso",
        "sessions_revogadas": revogadas,
    }
