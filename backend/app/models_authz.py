"""Modelos de permissoes e perfis de acesso extraidos de app.models."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.base_models import BaseTenantModel
from app.db import Base


class Role(BaseTenantModel):
    """Role (Função/Cargo) por tenant"""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"


class Permission(Base):
    """Permission (Permissão global do sistema)"""

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<Permission(id={self.id}, code={self.code})>"


class UserTenant(BaseTenantModel):
    """Vínculo User ↔ Tenant ↔ Role"""

    __tablename__ = "user_tenants"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<UserTenant(user_id={self.user_id}, tenant_id={self.tenant_id}, role_id={self.role_id})>"


class AppAccessProfile(BaseTenantModel):
    """Perfil operacional do app liberado para uma pessoa."""

    __tablename__ = "app_access_profiles"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "cliente_id",
            "profile_type",
            name="uq_app_access_profiles_tenant_cliente_profile",
        ),
        Index(
            "ix_app_access_profiles_tenant_user_profile",
            "tenant_id",
            "user_id",
            "profile_type",
        ),
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    profile_type = Column(String(30), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    granted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return (
            f"<AppAccessProfile(cliente_id={self.cliente_id}, "
            f"profile_type={self.profile_type}, tenant_id={self.tenant_id})>"
        )


class RolePermission(BaseTenantModel):
    """Vínculo Role ↔ Permission por tenant"""

    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    permission_id = Column(
        Integer, ForeignKey("permissions.id"), nullable=False, index=True
    )

    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id}, tenant_id={self.tenant_id})>"
