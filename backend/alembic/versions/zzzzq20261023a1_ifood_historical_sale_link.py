"""Explicit audited sale link for historical iFood cost.

Revision ID: zzzzq20261023a1
Revises: zzzzp20261023a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "zzzzq20261023a1"
down_revision = "zzzzp20261023a1"
branch_labels = None
depends_on = None
TABLE = "ifood_financial_sale_links"


def upgrade():
    op.create_index("ux_vendas_tenant_id", "vendas", ["tenant_id", "id"], unique=True)
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("merchant_id", sa.String(36), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("order_id", sa.String(80), nullable=False),
        sa.Column("venda_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("source_note", sa.String(1000), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("item_manifest", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "venda_id"],
            ["vendas.tenant_id", "vendas.id"],
            name="fk_ifood_fin_sale_link_tenant_sale",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "mode",
            "order_id",
            name="uq_ifood_fin_sale_link_order",
        ),
        sa.UniqueConstraint(
            "tenant_id", "mode", "venda_id", name="uq_ifood_fin_sale_link_sale"
        ),
        sa.CheckConstraint(
            "source = 'explicit_confirmation'", name="ck_ifood_fin_link_source"
        ),
        sa.CheckConstraint("mode = 'homologation'", name="ck_ifood_fin_link_mode"),
        sa.CheckConstraint("actor_id > 0", name="ck_ifood_fin_link_actor"),
    )
    op.create_index(f"ix_{TABLE}_tenant_id", TABLE, ["tenant_id"])
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=(TABLE,), enable=True)
    if op.get_bind().dialect.name == "postgresql":
        # O vinculo e a confirmacao original nao sao reescritos silenciosamente.
        op.execute("""
            CREATE FUNCTION ifood_fin_sale_link_immutable() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'O vinculo historico iFood e imutavel';
            END;
            $$ LANGUAGE plpgsql
        """)
        op.execute(f"""
            CREATE TRIGGER ifood_fin_sale_link_immutable
            BEFORE UPDATE OR DELETE ON {TABLE}
            FOR EACH ROW EXECUTE FUNCTION ifood_fin_sale_link_immutable()
        """)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"DROP TRIGGER ifood_fin_sale_link_immutable ON {TABLE}")
        op.execute("DROP FUNCTION ifood_fin_sale_link_immutable()")
    op.drop_table(TABLE)
    op.drop_index("ux_vendas_tenant_id", table_name="vendas")
