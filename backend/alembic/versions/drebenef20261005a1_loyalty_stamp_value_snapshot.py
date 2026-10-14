"""Guarda o passo historico do carimbo concedido por venda.

Revision ID: drebenef20261005a1
Revises: drecost20261005a1
"""

from alembic import op
import sqlalchemy as sa

revision = "drebenef20261005a1"
down_revision = "drecost20261005a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "loyalty_stamps",
        sa.Column("stamp_value_snapshot", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "loyalty_stamps", sa.Column("voided_origin", sa.String(20), nullable=True)
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION loyalty_stamp_value_snapshot_write_once() RETURNS trigger AS $$
            BEGIN
              IF OLD.stamp_value_snapshot IS NOT NULL
                 AND OLD.stamp_value_snapshot IS DISTINCT FROM NEW.stamp_value_snapshot
              THEN
                RAISE EXCEPTION 'stamp_value_snapshot de loyalty_stamp e imutavel';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """)
        op.execute("""
            CREATE TRIGGER trg_loyalty_stamp_value_snapshot_write_once
            BEFORE UPDATE OF stamp_value_snapshot ON loyalty_stamps
            FOR EACH ROW EXECUTE FUNCTION loyalty_stamp_value_snapshot_write_once()
            """)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_loyalty_stamp_value_snapshot_write_once ON loyalty_stamps"
        )
        op.execute("DROP FUNCTION IF EXISTS loyalty_stamp_value_snapshot_write_once()")
    op.drop_column("loyalty_stamps", "voided_origin")
    op.drop_column("loyalty_stamps", "stamp_value_snapshot")
