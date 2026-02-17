# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.db import get_session as get_db
from app.auth import get_current_user_and_tenant
from app.security.permissions_decorator import require_permission
from app.models import Permission

router = APIRouter(tags=["Permissions"])


class PermissionResponse(BaseModel):
    permission_id: int
    nome: str
    descricao: str | None = None

    class Config:
        from_attributes = True


@router.get("/permissions", response_model=List[PermissionResponse])
def listar_permissions(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todas as permissões disponíveis"""
    permissions = db.query(Permission).order_by(Permission.code).all()
    return [
        {
            "permission_id": p.id,
            "nome": p.code,
            "descricao": p.description
        }
        for p in permissions
    ]


@router.get("/permissions-map")
@require_permission("usuarios.manage")
def permissions_map(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    perms = db.query(Permission.id, Permission.code).order_by(Permission.code).all()
    return [{"id": p.id, "code": p.code} for p in perms]
