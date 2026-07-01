"""Favoritos do menu lateral por usuario."""

from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class UsuarioMenuFavorito(BaseTenantModel):
    """Atalho favoritado por usuario dentro de um tenant."""

    __tablename__ = "usuario_menu_favoritos"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "path",
            name="uq_usuario_menu_favoritos_tenant_user_path",
        ),
        Index(
            "ix_usuario_menu_favoritos_tenant_user_position",
            "tenant_id",
            "user_id",
            "position",
        ),
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    path = Column(String(255), nullable=False)
    label = Column(String(120), nullable=False)
    icon_key = Column(String(80), nullable=True)
    position = Column(Integer, nullable=False, default=0)

    user = relationship("User")
