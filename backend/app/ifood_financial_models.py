"""Evidencias financeiras iFood e custos informados, isolados por empresa."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
    text,
)

from app.base_models import BaseTenantModel


class IfoodFinancialSnapshot(BaseTenantModel):
    __tablename__ = "ifood_financial_snapshots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_ifood_fin_snapshot_tenant_id"),
        UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "mode",
            "begin_date",
            "end_date",
            "revision",
            name="uq_ifood_fin_snapshot_revision",
        ),
        Index(
            "uq_ifood_fin_snapshot_current",
            "tenant_id",
            "merchant_id",
            "mode",
            "begin_date",
            "end_date",
            unique=True,
            postgresql_where=text("active = true"),
            sqlite_where=text("active = 1"),
        ),
        CheckConstraint("end_date >= begin_date", name="ck_ifood_fin_snapshot_period"),
        CheckConstraint("revision > 0", name="ck_ifood_fin_snapshot_revision"),
    )

    merchant_id = Column(String(36), nullable=False)
    mode = Column(String(20), nullable=False)
    begin_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    revision = Column(Integer, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    source = Column(String(40), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    page_count = Column(Integer, nullable=False)
    event_count = Column(Integer, nullable=False)
    actor_id = Column(Integer, nullable=False)


class IfoodFinancialEvent(BaseTenantModel):
    __tablename__ = "ifood_financial_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "snapshot_id"],
            ["ifood_financial_snapshots.tenant_id", "ifood_financial_snapshots.id"],
            ondelete="RESTRICT",
            name="fk_ifood_fin_event_tenant_snapshot",
        ),
        UniqueConstraint("snapshot_id", "position", name="uq_ifood_fin_event_position"),
        Index("ix_ifood_fin_event_order", "tenant_id", "order_id"),
        CheckConstraint("position > 0", name="ck_ifood_fin_event_position"),
    )

    snapshot_id = Column(Integer, nullable=False)
    position = Column(Integer, nullable=False)
    order_id = Column(String(80), nullable=True)
    name = Column(String(100), nullable=False)
    trigger = Column(String(100), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    has_transfer_impact = Column(Boolean, nullable=False)
    # Allowlist tecnica; nao guarda merchantDocument nem dados de consumidor.
    evidence = Column(JSON, nullable=False)


class IfoodFinancialOrderCosts(BaseTenantModel):
    __tablename__ = "ifood_financial_order_costs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "mode",
            "order_id",
            "version",
            name="uq_ifood_fin_order_cost_version",
        ),
        Index(
            "ix_ifood_fin_order_cost_scope",
            "tenant_id",
            "merchant_id",
            "mode",
            "order_id",
        ),
        CheckConstraint("version > 0", name="ck_ifood_fin_cost_version"),
        CheckConstraint("revenue IS NULL OR revenue >= 0", name="ck_ifood_fin_revenue"),
        CheckConstraint("cmv IS NULL OR cmv >= 0", name="ck_ifood_fin_cmv"),
        CheckConstraint("tax IS NULL OR tax >= 0", name="ck_ifood_fin_tax"),
        CheckConstraint(
            "other_costs IS NULL OR other_costs >= 0",
            name="ck_ifood_fin_other_costs",
        ),
    )

    merchant_id = Column(String(36), nullable=False)
    mode = Column(String(20), nullable=False)
    order_id = Column(String(80), nullable=False)
    version = Column(Integer, nullable=False)
    revenue = Column(Numeric(18, 2), nullable=True)
    cmv = Column(Numeric(18, 2), nullable=True)
    tax = Column(Numeric(18, 2), nullable=True)
    other_costs = Column(Numeric(18, 2), nullable=True)
    source_note = Column(String(1000), nullable=False)
    actor_id = Column(Integer, nullable=False)
