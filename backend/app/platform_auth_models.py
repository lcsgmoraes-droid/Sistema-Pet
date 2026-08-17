"""Identidades e sessões globais dos administradores da plataforma CorePet."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db import Base


class PlatformAdmin(Base):
    """Administrador do CorePet, sem vínculo com qualquer tenant cliente."""

    __tablename__ = "platform_admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)

    failed_login_attempts = Column(
        Integer, nullable=False, default=0, server_default="0"
    )
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(50), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    sessions = relationship(
        "PlatformAdminSession",
        back_populates="admin",
        cascade="all, delete-orphan",
    )


class PlatformAdminSession(Base):
    """Sessão revogável e independente das sessões dos usuários de tenants."""

    __tablename__ = "platform_admin_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_admin_id = Column(
        Integer,
        ForeignKey("platform_admins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_jti = Column(String(36), nullable=False, unique=True, index=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked = Column(Boolean, nullable=False, default=False, server_default="false")
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoke_reason = Column(String(255), nullable=True)

    admin = relationship("PlatformAdmin", back_populates="sessions")
