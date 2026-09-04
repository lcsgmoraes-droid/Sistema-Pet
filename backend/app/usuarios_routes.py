import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, model_validator

from app.db import get_session
from app.auth import get_current_user_and_tenant
from app.auth.core import hash_password
from app.security.permissions_decorator import require_permission
from app.models import User, UserTenant, Role
from app.usuario_menu_favoritos_models import UsuarioMenuFavorito
from app.services.business_audit_service import (
    build_user_access_metadata,
    log_business_event,
)
from app.services.auth_security import register_password_changed
from app.services.user_account_service import (
    UserAccountError,
    create_tenant_user_account,
    email_exists_globally,
    is_unique_email_violation,
    is_unique_username_violation,
    normalize_username,
    username_exists_in_tenant,
    validate_password,
)
from app.session_manager import revoke_all_sessions
from app.tenancy.rls import sync_rls_auth_user

router = APIRouter(prefix="/usuarios", tags=["Usuários"])
MAX_MENU_FAVORITOS = 8


class UserCreate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None
    nome: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    role_id: int  # Role a ser vinculada ao usuário

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.username and not self.email:
            raise ValueError("Informe o nome de usuario ou o e-mail")
        return self


class UsuarioListResponse(BaseModel):
    user_id: int
    username: str | None = None
    email: str | None = None
    nome: str | None = None
    role_id: int
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    username: str | None = None
    email: str | None = None
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
    new_password: str | None = Field(default=None, min_length=8, max_length=72)
    generate_password: bool = False
    role_id: int | None = None

    @model_validator(mode="after")
    def validate_change(self):
        if (
            self.username is None
            and self.new_password is None
            and not self.generate_password
            and self.role_id is None
        ):
            raise ValueError("Informe o nome de usuario, uma nova senha ou um perfil")
        if self.new_password is not None and self.generate_password:
            raise ValueError("Escolha uma senha ou gere uma senha, nao as duas opcoes")
        return self


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


def _is_unique_email_violation(exc: IntegrityError) -> bool:
    return is_unique_email_violation(exc)


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
            User.nome,
            Role.id.label("role_id"),
            Role.name.label("role"),
            UserTenant.is_active,
        )
        .join(UserTenant, UserTenant.user_id == User.id)
        .join(Role, Role.id == UserTenant.role_id)
        .filter(UserTenant.tenant_id == tenant_id)
        .all()
    )

    return rows


@router.post("", response_model=UserResponse)
@require_permission("usuarios.manage")
def criar_usuario(
    payload: UserCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    actor, tenant_id = user_and_tenant

    try:
        user, role = create_tenant_user_account(
            db,
            tenant_id=tenant_id,
            username=payload.username,
            email=payload.email,
            password=payload.password,
            role_id=payload.role_id,
            nome=payload.nome,
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
                extra={"is_active": True},
            ),
            details=f"Usuario {user.username or user.email} criado no tenant",
            commit=False,
        )
        db.commit()
        db.refresh(user)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nao foi possivel criar o usuario agora. Tente novamente em instantes.",
        ) from exc

    return user


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
    password_changed = False
    role_changed = False
    selected_role: Role | None = None
    generated_password: str | None = None

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
            role_changed = vinculo.role_id != selected_role.id
            vinculo.role_id = selected_role.id

        if password_changed or role_changed:
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
        raise

    return {
        "status": "ok",
        "username": target_user.username,
        "password_changed": password_changed,
        "role_changed": role_changed,
        "role_id": vinculo.role_id,
        "generated_password": generated_password,
        "sessions_revoked": sessions_revoked,
    }


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
