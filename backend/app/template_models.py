from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base
from app.base_models import TenantScoped


class TemplateBundle(Base):
    """Global, system-owned template package."""

    __tablename__ = "template_bundles"
    __table_args__ = (
        UniqueConstraint("bundle_code", "version", name="uq_template_bundles_code_version"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    bundle_code = Column(String(80), nullable=False, index=True)
    version = Column(String(40), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TemplateItem(Base):
    """Global template item copied into tenant-owned tables during onboarding."""

    __tablename__ = "template_items"
    __table_args__ = (
        UniqueConstraint(
            "bundle_code",
            "bundle_version",
            "item_type",
            "template_code",
            name="uq_template_items_bundle_type_code",
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    bundle_code = Column(String(80), nullable=False, index=True)
    bundle_version = Column(String(40), nullable=False, index=True)
    item_type = Column(String(80), nullable=False, index=True)
    template_code = Column(String(120), nullable=False, index=True)
    name = Column(String(180), nullable=False)
    payload = Column(JSON, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TenantTemplateInstall(TenantScoped, Base):
    """Audit record for template bundles applied to a tenant.

    tenant_id vem do mixin TenantScoped (UUID NOT NULL, indexado) -> entra no filtro
    global de tenant. Schema identico ao anterior; sem migration.
    """

    __tablename__ = "tenant_template_installs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "bundle_code",
            "bundle_version",
            name="uq_tenant_template_installs_tenant_bundle_version",
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    # tenant_id: herdado do mixin TenantScoped (UUID NOT NULL, indexado).
    bundle_code = Column(String(80), nullable=False, index=True)
    bundle_version = Column(String(40), nullable=False, index=True)
    status = Column(String(40), nullable=False, default="completed")
    dry_run = Column(Boolean, nullable=False, default=False)
    created_by_user_id = Column(Integer, nullable=True)
    summary = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TenantTemplateItemInstall(TenantScoped, Base):
    """Item-level link between a global template item and a tenant-owned copy.

    tenant_id vem do mixin TenantScoped (UUID NOT NULL, indexado) -> entra no filtro
    global de tenant. Schema identico ao anterior; sem migration.
    """

    __tablename__ = "tenant_template_item_installs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "bundle_code",
            "bundle_version",
            "item_type",
            "template_code",
            name="uq_tenant_template_item_installs_template",
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    # tenant_id: herdado do mixin TenantScoped (UUID NOT NULL, indexado).
    bundle_code = Column(String(80), nullable=False, index=True)
    bundle_version = Column(String(40), nullable=False, index=True)
    item_type = Column(String(80), nullable=False, index=True)
    template_code = Column(String(120), nullable=False, index=True)
    target_table = Column(String(120), nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    status = Column(String(40), nullable=False, default="active")
    created_by_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
