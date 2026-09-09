"""Carteira por empresa e operações auditáveis, sem criação automática de saldo."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    event,
)
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.base_models import TenantScoped
from app.db.base_class import Base


class UUIDString(TypeDecorator):
    """UUID canônico em texto para os IDs de operações e lançamentos."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(UUID(str(value))) if value is not None else None


# O filtro ORM global usa UUID nativo. A referência calculada preserva a FK para
# tenants.id VARCHAR legado sem um segundo identificador mutável vindo da API.
_UUID_HEX = "replace(CAST(tenant_id AS VARCHAR), '-', '')"
TENANT_REFERENCE_EXPRESSION = (
    f"substr({_UUID_HEX},1,8)||'-'||substr({_UUID_HEX},9,4)||'-'||"
    f"substr({_UUID_HEX},13,4)||'-'||substr({_UUID_HEX},17,4)||'-'||substr({_UUID_HEX},21,12)"
)


def _tenant_reference():
    return Column(
        String(36),
        Computed(TENANT_REFERENCE_EXPRESSION, persisted=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )


class CreditoWallet(TenantScoped, Base):
    __tablename__ = "creditos_wallets"
    __table_args__ = (
        CheckConstraint("available_credits >= 0", name="ck_creditos_wallet_available"),
        CheckConstraint("reserved_credits >= 0", name="ck_creditos_wallet_reserved"),
        CheckConstraint("version >= 0", name="ck_creditos_wallet_version"),
    )

    tenant_id = Column(PGUUID(as_uuid=True), primary_key=True)
    tenant_ref_id = _tenant_reference()
    available_credits = Column(Integer, nullable=False, default=0, server_default="0")
    reserved_credits = Column(Integer, nullable=False, default=0, server_default="0")
    version = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CreditoOperation(TenantScoped, Base):
    __tablename__ = "creditos_operations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_creditos_operation_key"
        ),
        UniqueConstraint("tenant_id", "id", name="uq_creditos_operation_tenant_id"),
        CheckConstraint(
            "credits > 0 AND price_cents > 0", name="ck_creditos_operation_price"
        ),
        CheckConstraint(
            "mode IN ('shadow','enforced')", name="ck_creditos_operation_mode"
        ),
        CheckConstraint(
            "status IN ('quoted','running','completed','failed','uncertain')",
            name="ck_creditos_operation_status",
        ),
        Index("ix_creditos_operation_tenant_created", "tenant_id", "created_at"),
    )

    id = Column(UUIDString(), primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False)
    tenant_ref_id = _tenant_reference()
    actor_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    idempotency_key = Column(String(128), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    service_code = Column(String(80), nullable=False)
    title = Column(String(160), nullable=False)
    credits = Column(Integer, nullable=False)
    price_cents = Column(Integer, nullable=False)
    tariff_version = Column(String(64), nullable=False)
    mode = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False, default="quoted")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result_payload = Column(JSON, nullable=True)
    usage_metadata = Column(JSON, nullable=True)
    failure_code = Column(String(64), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CreditoLedgerEntry(TenantScoped, Base):
    __tablename__ = "creditos_ledger"
    __table_args__ = (
        UniqueConstraint("tenant_id", "event_key", name="uq_creditos_ledger_event"),
        ForeignKeyConstraint(
            ["tenant_id", "operation_id"],
            ["creditos_operations.tenant_id", "creditos_operations.id"],
            name="fk_creditos_ledger_tenant_operation",
            ondelete="RESTRICT",
        ),
        CheckConstraint("credits > 0", name="ck_creditos_ledger_credits"),
        CheckConstraint(
            "kind IN ('grant','reserve','capture','release','shadow_usage')",
            name="ck_creditos_ledger_kind",
        ),
        CheckConstraint(
            "available_after IS NULL OR available_after >= 0",
            name="ck_creditos_ledger_available",
        ),
        CheckConstraint(
            "reserved_after IS NULL OR reserved_after >= 0",
            name="ck_creditos_ledger_reserved",
        ),
        Index("ix_creditos_ledger_tenant_created", "tenant_id", "created_at"),
    )

    id = Column(UUIDString(), primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False)
    tenant_ref_id = _tenant_reference()
    operation_id = Column(UUIDString(), nullable=True)
    actor_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    event_key = Column(String(160), nullable=False)
    kind = Column(String(24), nullable=False)
    service_code = Column(String(80), nullable=True)
    title = Column(String(160), nullable=False)
    credits = Column(Integer, nullable=False)
    mode = Column(String(16), nullable=False)
    available_delta = Column(Integer, nullable=False, default=0)
    reserved_delta = Column(Integer, nullable=False, default=0)
    available_after = Column(Integer, nullable=True)
    reserved_after = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


def _reject_ledger_mutation(*_args, **_kwargs):
    raise ValueError(
        "O extrato de créditos é imutável; use um lançamento compensatório."
    )


event.listen(CreditoLedgerEntry, "before_update", _reject_ledger_mutation)
event.listen(CreditoLedgerEntry, "before_delete", _reject_ledger_mutation)
