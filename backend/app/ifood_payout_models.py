"""Read-only provider evidence; no bank receipt or ledger posting is implied."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    text,
)

from app.base_models import BaseTenantModel


class IfoodPayoutSnapshot(BaseTenantModel):
    __tablename__ = "ifood_payout_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "mode",
            "kind",
            "basis",
            "begin_date",
            "end_date",
            "revision",
            name="uq_ifood_payout_revision",
        ),
        Index(
            "uq_ifood_payout_current",
            "tenant_id",
            "merchant_id",
            "mode",
            "kind",
            "basis",
            "begin_date",
            "end_date",
            unique=True,
            postgresql_where=text("active = true"),
            sqlite_where=text("active = 1"),
        ),
        CheckConstraint(
            "kind IN ('settlements','statement')", name="ck_ifood_payout_kind"
        ),
        CheckConstraint(
            "basis IN ('calculation','payment','competence')",
            name="ck_ifood_payout_basis",
        ),
        CheckConstraint("mode = 'homologation'", name="ck_ifood_payout_mode"),
        CheckConstraint(
            "revision > 0 AND end_date >= begin_date", name="ck_ifood_payout_period"
        ),
    )
    merchant_id = Column(String(36), nullable=False)
    mode = Column(String(20), nullable=False)
    kind = Column(String(20), nullable=False)
    basis = Column(String(20), nullable=False)
    begin_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    revision = Column(Integer, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    source = Column(String(40), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    # Decimal strings, technical IDs and dates only. No signed URL/bank details.
    evidence = Column(JSON, nullable=False)
    actor_id = Column(Integer, nullable=False)


class IfoodReconciliationJob(BaseTenantModel):
    __tablename__ = "ifood_reconciliation_jobs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "mode",
            "competence",
            name="uq_ifood_recon_job_scope",
        ),
        CheckConstraint("mode = 'homologation'", name="ck_ifood_recon_job_mode"),
        CheckConstraint("attempts >= 0", name="ck_ifood_recon_attempts"),
    )
    merchant_id = Column(String(36), nullable=False)
    mode = Column(String(20), nullable=False)
    competence = Column(String(7), nullable=False)
    request_id = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    next_check_at = Column(DateTime(timezone=True), nullable=True)
    imported = Column(Boolean, default=False, nullable=False)
    last_error = Column(String(250), nullable=True)
    actor_id = Column(Integer, nullable=False)
