from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db import get_session
from app.auth import get_current_user_and_tenant
from app.auth.core import hash_password
from app.security.permissions_decorator import require_permission
from app.models import User, UserTenant, Role
from app.services.business_audit_service import build_user_access_metadata, log_business_event
from app.session_manager import revoke_all_sessions
from app.tenancy.rls import sync_rls_auth_email, sync_rls_auth_user

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role_id: int  # Role a ser vinculada ao usuário


class UsuarioListResponse(BaseModel):
    user_id: int
    email: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool

    class Config:
        from_attributes = True


def _email_ja_cadastrado_globalmente(db: Session, email: str) -> bool:
    """Users.email tem unicidade global; a checagem precisa ignorar o filtro de tenant."""
    sync_rls_auth_email(db, email)
    row = db.execute(
        text("SELECT id FROM users WHERE lower(email) = :email LIMIT 1"),
        {"email": email},
    ).first()
    return row is not None


def _is_unique_email_violation(exc: IntegrityError) -> bool:
    error_text = str(getattr(exc, "orig", exc)).lower()
    return (
        "users_email" in error_text
        or "users.email" in error_text
        or ("unique" in error_text and "email" in error_text)
    )


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
            User.email,
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
    email = payload.email.strip().lower()
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Senha deve ter no minimo 8 caracteres. Use uma senha com 8 caracteres ou mais.",
        )

    if _email_ja_cadastrado_globalmente(db, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail ja esta cadastrado. Use outro e-mail ou verifique se o usuario ja existe em outro tenant.",
        )

    role = (
        db.query(Role)
        .filter(Role.id == payload.role_id, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(
            status_code=400,
            detail="Perfil de acesso invalido para este tenant. Atualize a pagina e selecione um perfil novamente.",
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        is_active=True,
        tenant_id=tenant_id,
        email_verified=True,
        email_verified_at=datetime.now(timezone.utc),
    )

    try:
        db.add(user)
        db.flush()

        vinculo = UserTenant(
            user_id=user.id,
            tenant_id=tenant_id,
            role_id=role.id,
            is_active=True,
        )
        db.add(vinculo)
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
            details=f"Usuario {user.email} criado no tenant",
            commit=False,
        )
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        if _is_unique_email_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este e-mail ja esta cadastrado. Use outro e-mail ou verifique se o usuario ja existe em outro tenant.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nao foi possivel criar o usuario agora. Tente novamente em instantes.",
        ) from exc

    return user


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
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == tenant_id)
        .first()
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
        raise HTTPException(status_code=400, detail="Usuário já vinculado a este tenant")

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
        details=f"Usuario {user.email} vinculado ao tenant",
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
        raise HTTPException(status_code=404, detail="Usuário não vinculado a este tenant")

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
                    UserTenant.is_active == True,
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
        raise HTTPException(status_code=404, detail="Usuário não vinculado a este tenant")

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
