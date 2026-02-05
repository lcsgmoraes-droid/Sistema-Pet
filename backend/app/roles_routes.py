# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db import get_session as get_db
from app.auth import get_current_user_and_tenant
from app.tenancy.context import get_current_tenant
from app.security.permissions_decorator import require_permission
from app.models import Role, Permission, RolePermission, UserTenant

router = APIRouter(prefix="/roles", tags=["Roles"])


# =========================
# MODELS
# =========================

class RoleCreate(BaseModel):
    nome: str
    descricao: str | None = None
    permissions: list[int] = []


class RoleResponse(BaseModel):
    id: int
    name: str


class PermissionsUpdate(BaseModel):
    permission_ids: list[int]


# =========================
# C1 - CRUD DE ROLES
# =========================

@router.get("", response_model=list[dict])
def listar_roles(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista roles com suas permissões"""
    current_user, tenant_id = user_and_tenant
    roles = db.query(Role).filter(Role.tenant_id == tenant_id).all()
    
    result = []
    for role in roles:
        # Buscar permiss�es da role
        perms = (
            db.query(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(
                RolePermission.role_id == role.id,
                RolePermission.tenant_id == tenant_id
            )
            .all()
        )
        
        result.append({
            "role_id": role.id,
            "nome": role.name,
            "descricao": None,
            "permissions": [
                {
                    "permission_id": p.id,
                    "nome": p.code,
                    "descricao": p.description
                }
                for p in perms
            ]
        })
    
    return result


@router.post("", response_model=dict)
def criar_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    exists = (
        db.query(Role)
        .filter(Role.tenant_id == tenant_id, Role.name == payload.nome)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Role j� existe")

    role = Role(name=payload.nome, tenant_id=tenant_id)
    db.add(role)
    db.flush()
    
    # Adicionar permiss�es
    for perm_id in payload.permissions:
        db.add(RolePermission(
            tenant_id=tenant_id,
            role_id=role.id,
            permission_id=perm_id
        ))
    
    db.commit()
    db.refresh(role)
    
    # Buscar permiss�es para retornar
    perms = (
        db.query(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(
            RolePermission.role_id == role.id,
            RolePermission.tenant_id == tenant_id
        )
        .all()
    )
    
    return {
        "role_id": role.id,
        "nome": role.name,
        "descricao": None,
        "permissions": [
            {
                "permission_id": p.id,
                "nome": p.code,
                "descricao": p.description
            }
            for p in perms
        ]
    }


@router.put("/{role_id}", response_model=dict)
def atualizar_role(
    role_id: int,
    payload: RoleCreate,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    role = (
        db.query(Role)
        .filter(Role.id == role_id, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role n�o encontrado")

    role.name = payload.nome
    
    # Remover permiss�es antigas
    db.query(RolePermission).filter(
        RolePermission.role_id == role_id,
        RolePermission.tenant_id == tenant_id
    ).delete()
    
    # Adicionar novas permiss�es
    for perm_id in payload.permissions:
        db.add(RolePermission(
            tenant_id=tenant_id,
            role_id=role.id,
            permission_id=perm_id
        ))
    
    db.commit()
    db.refresh(role)
    
    # Buscar permiss�es para retornar
    perms = (
        db.query(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(
            RolePermission.role_id == role.id,
            RolePermission.tenant_id == tenant_id
        )
        .all()
    )
    
    return {
        "role_id": role.id,
        "nome": role.name,
        "descricao": None,
        "permissions": [
            {
                "permission_id": p.id,
                "nome": p.code,
                "descricao": p.description
            }
            for p in perms
        ]
    }


@router.delete("/{role_id}", status_code=204)
def deletar_role(
    role_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    in_use = (
        db.query(UserTenant)
        .filter(UserTenant.role_id == role_id, UserTenant.tenant_id == tenant_id)
        .first()
    )
    if in_use:
        raise HTTPException(status_code=400, detail="Role est� em uso")

    role = (
        db.query(Role)
        .filter(Role.id == role_id, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role n�o encontrado")

    db.delete(role)
    db.commit()
    return {"status": "ok"}


# =========================
# C2 � PERMISS�ES DO ROLE
# =========================

@router.get("/permissions", response_model=list[str])
@require_permission("usuarios.manage")
def listar_permissoes(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    perms = db.query(Permission.code).order_by(Permission.code).all()
    return [p[0] for p in perms]


@router.get("/{role_id}/permissions", response_model=list[str])
@require_permission("usuarios.manage")
def permissoes_do_role(
    role_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    role = (
        db.query(Role)
        .filter(Role.id == role_id, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role n�o encontrado")

    rows = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(
            RolePermission.role_id == role_id,
            RolePermission.tenant_id == tenant_id,
        )
        .all()
    )

    return [r[0] for r in rows]


@router.put("/{role_id}/permissions")
@require_permission("usuarios.manage")
def atualizar_permissoes_role(
    role_id: int,
    payload: PermissionsUpdate,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    role = (
        db.query(Role)
        .filter(Role.id == role_id, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role n�o encontrado")

    db.query(RolePermission).filter(
        RolePermission.role_id == role_id,
        RolePermission.tenant_id == tenant_id,
    ).delete()

    for perm_id in payload.permission_ids:
        db.add(
            RolePermission(
                tenant_id=tenant_id,
                role_id=role_id,
                permission_id=perm_id,
            )
        )

    db.commit()
    return {"status": "ok"}
