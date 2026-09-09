"""Base de créditos sem pagamentos, seed de saldo ou ativação automática."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import iter_tenant_rls_statements


revision = "zzm20260909a1"
down_revision = "zzl20260909a1"
branch_labels = None
depends_on = None

TABLES = ("creditos_wallets", "creditos_operations", "creditos_ledger")


def _tenant_type():
    # Há instalações históricas com tenants.id VARCHAR(36) e outras UUID.
    # A FK precisa acompanhar o tipo físico, sem alterar a tabela global.
    columns = sa.inspect(op.get_bind()).get_columns("tenants")
    return next(column["type"].copy() for column in columns if column["name"] == "id")


def _tenant_columns(tenant_type, *, primary_key=False):
    # O identificador filtrado pelo ORM e RLS deve ser UUID. A FK calculada
    # imutável resolve o legado tenants.id VARCHAR sem alterar a tabela global.
    uuid_hex = "replace(CAST(tenant_id AS VARCHAR), '-', '')"
    expression = (
        f"substr({uuid_hex},1,8)||'-'||substr({uuid_hex},9,4)||'-'||"
        f"substr({uuid_hex},13,4)||'-'||substr({uuid_hex},17,4)||'-'||substr({uuid_hex},21,12)"
    )
    if isinstance(tenant_type, sa.Uuid):
        expression = "tenant_id"
    return [
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=primary_key,
        ),
        sa.Column(
            "tenant_ref_id",
            tenant_type.copy(),
            sa.Computed(expression, persisted=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    ]


def _created_at():
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


def _updated_at():
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


def upgrade():
    tenant_type = _tenant_type()
    op.create_table(
        "creditos_wallets",
        *_tenant_columns(tenant_type, primary_key=True),
        sa.Column(
            "available_credits", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("reserved_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint(
            "available_credits >= 0", name="ck_creditos_wallet_available"
        ),
        sa.CheckConstraint("reserved_credits >= 0", name="ck_creditos_wallet_reserved"),
        sa.CheckConstraint("version >= 0", name="ck_creditos_wallet_version"),
        if_not_exists=True,
    )
    op.create_table(
        "creditos_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tenant_columns(tenant_type),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("service_code", sa.String(80), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("tariff_version", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("usage_metadata", sa.JSON(), nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_creditos_operation_key"
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_creditos_operation_tenant_id"),
        sa.CheckConstraint(
            "credits > 0 AND price_cents > 0", name="ck_creditos_operation_price"
        ),
        sa.CheckConstraint(
            "mode IN ('shadow','enforced')", name="ck_creditos_operation_mode"
        ),
        sa.CheckConstraint(
            "status IN ('quoted','running','completed','failed','uncertain')",
            name="ck_creditos_operation_status",
        ),
        if_not_exists=True,
    )
    op.create_table(
        "creditos_ledger",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tenant_columns(tenant_type),
        sa.Column("operation_id", sa.String(36), nullable=True),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_key", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("service_code", sa.String(80), nullable=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("available_delta", sa.Integer(), nullable=False),
        sa.Column("reserved_delta", sa.Integer(), nullable=False),
        sa.Column("available_after", sa.Integer(), nullable=True),
        sa.Column("reserved_after", sa.Integer(), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "operation_id"],
            ["creditos_operations.tenant_id", "creditos_operations.id"],
            ondelete="RESTRICT",
            name="fk_creditos_ledger_tenant_operation",
        ),
        sa.UniqueConstraint("tenant_id", "event_key", name="uq_creditos_ledger_event"),
        sa.CheckConstraint("credits > 0", name="ck_creditos_ledger_credits"),
        sa.CheckConstraint(
            "kind IN ('grant','reserve','capture','release','shadow_usage')",
            name="ck_creditos_ledger_kind",
        ),
        sa.CheckConstraint(
            "available_after IS NULL OR available_after >= 0",
            name="ck_creditos_ledger_available",
        ),
        sa.CheckConstraint(
            "reserved_after IS NULL OR reserved_after >= 0",
            name="ck_creditos_ledger_reserved",
        ),
        if_not_exists=True,
    )
    for name, table in (
        ("ix_creditos_operation_tenant_created", "creditos_operations"),
        ("ix_creditos_ledger_tenant_created", "creditos_ledger"),
    ):
        op.create_index(name, table, ["tenant_id", "created_at"], if_not_exists=True)

    if op.get_bind().dialect.name == "postgresql":
        for table in TABLES:
            for statement in iter_tenant_rls_statements(table, enable=True):
                op.execute(statement)
        op.execute("""
            CREATE OR REPLACE FUNCTION creditos_reject_ledger_mutation()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'creditos_ledger is append-only; use a compensating entry';
            END;
            $$
        """)
        op.execute(
            "DROP TRIGGER IF EXISTS creditos_ledger_immutable ON creditos_ledger"
        )
        op.execute("""
            CREATE TRIGGER creditos_ledger_immutable BEFORE UPDATE OR DELETE ON creditos_ledger
            FOR EACH ROW EXECUTE FUNCTION creditos_reject_ledger_mutation()
        """)
        op.execute(
            "DROP TRIGGER IF EXISTS creditos_ledger_no_truncate ON creditos_ledger"
        )
        op.execute("""
            CREATE TRIGGER creditos_ledger_no_truncate BEFORE TRUNCATE ON creditos_ledger
            FOR EACH STATEMENT EXECUTE FUNCTION creditos_reject_ledger_mutation()
        """)


def downgrade():
    # Não há dados preexistentes migrados nem saldo/flags a desfazer.
    for table in reversed(TABLES):
        op.drop_table(table, if_exists=True)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS creditos_reject_ledger_mutation()")
