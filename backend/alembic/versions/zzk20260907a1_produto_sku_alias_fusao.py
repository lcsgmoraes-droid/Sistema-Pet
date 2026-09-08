"""Aliases de SKU separados de EAN e auditoria da fusao de produtos."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "zzk20260907a1"
down_revision = "zzj20260905a1"
branch_labels = None
depends_on = None


def _base():
    return [
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
    ]


def upgrade():
    op.add_column(
        "produto_bling_sync",
        sa.Column("retirado_para_produto_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_bling_sync_retirado_produto",
        "produto_bling_sync",
        "produtos",
        ["retirado_para_produto_id"],
        ["id"],
    )
    op.create_table(
        "produto_sku_aliases",
        *_base(),
        sa.Column(
            "produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False
        ),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("sku_normalizado", sa.String(200), nullable=False),
        sa.Column("origem", sa.String(40), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "sku_normalizado", name="uq_produto_sku_alias_tenant_sku"
        ),
    )
    op.create_index(
        "ix_produto_sku_aliases_produto_id", "produto_sku_aliases", ["produto_id"]
    )
    op.create_table(
        "produto_fusao_logs",
        *_base(),
        sa.Column("principal_id", sa.Integer(), nullable=False),
        sa.Column("duplicado_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("estrategia_estoque", sa.String(30), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("antes", sa.JSON(), nullable=False),
        sa.Column("depois", sa.JSON(), nullable=False),
        sa.Column("referencias", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "duplicado_id", name="uq_produto_fusao_tenant_duplicado"
        ),
    )
    for table in ("produto_sku_aliases", "produto_fusao_logs"):
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        if op.get_bind().dialect.name == "postgresql":
            guard = (
                "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
            )
            target = ""
            if table == "produto_sku_aliases":
                target = " AND EXISTS (SELECT 1 FROM produtos p WHERE p.id = produto_id AND p.tenant_id = produto_sku_aliases.tenant_id)"
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            op.execute(
                f"CREATE POLICY {table}_tenant_isolation ON {table} USING ({guard}) WITH CHECK ({guard}{target})"
            )


def downgrade():
    op.drop_table("produto_fusao_logs")
    op.drop_table("produto_sku_aliases")
    op.drop_constraint(
        "fk_bling_sync_retirado_produto", "produto_bling_sync", type_="foreignkey"
    )
    op.drop_column("produto_bling_sync", "retirado_para_produto_id")
