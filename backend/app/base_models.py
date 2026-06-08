"""
Base model for multi-tenant tables
"""
from sqlalchemy import Column, Integer, DateTime, Identity
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr
from sqlalchemy.sql import func

from app.db import Base


class TenantScoped:
    """
    Marcador leve de modelo multi-tenant.

    Provê APENAS a coluna ``tenant_id`` (NOT NULL, indexada) e serve de alvo para
    o filtro global de tenant em ``app/tenancy/filters.py`` (injeção automática de
    ``WHERE tenant_id = ?`` + fail-fast).

    Use este mixin em modelos LEGADOS que herdam ``Base`` diretamente e não podem
    adotar ``BaseTenantModel`` por terem esquema próprio (ex.: ``id`` autoincrement,
    timestamps ``criado_em``/``atualizado_em`` em vez de ``created_at``/``updated_at``).
    Basta declarar ``class X(TenantScoped, Base)`` e NÃO declarar ``tenant_id`` na
    classe (ele vem do mixin), entrando assim no filtro automático sem alterar o schema.

    Modelos novos devem preferir ``BaseTenantModel`` (que já traz id/timestamps).
    """

    @declared_attr
    def tenant_id(cls):
        return Column(
            UUID(as_uuid=True),
            nullable=False,
            index=True,
        )


class BaseTenantModel(Base):
    """
    Base class for all multi-tenant models.
    Automatically adds id, tenant_id, created_at, and updated_at columns.
    
    The tenant_id is automatically injected by the before_flush event
    in db.py, so you don't need to manually set it when creating objects.
    
    The id uses Identity(always=True) to ensure PostgreSQL always generates it,
    preventing duplicate key violations.
    """
    __abstract__ = True

    @declared_attr
    def id(cls):
        return Column(
            Integer,
            Identity(always=True),
            primary_key=True
        )

    @declared_attr
    def tenant_id(cls):
        return Column(
            UUID(as_uuid=True),
            nullable=False,
            index=True,
        )

    @declared_attr
    def created_at(cls):
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        )

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False
        )
