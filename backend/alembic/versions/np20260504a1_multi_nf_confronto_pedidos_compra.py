"""allow multiple entry invoices per purchase order confrontation

Revision ID: np20260504a1
Revises: mo20260503a1
Create Date: 2026-05-04 14:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "np20260504a1"
down_revision = "mo20260503a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("pedidos_compra"):
        colunas_pedido = {
            coluna["name"] for coluna in inspector.get_columns("pedidos_compra")
        }
        if "nota_entrada_id" not in colunas_pedido:
            op.execute(
                "ALTER TABLE pedidos_compra "
                "ADD COLUMN IF NOT EXISTS nota_entrada_id INTEGER REFERENCES notas_entrada(id)"
            )
        if "data_confronto" not in colunas_pedido:
            op.execute(
                "ALTER TABLE pedidos_compra ADD COLUMN IF NOT EXISTS data_confronto TIMESTAMP"
            )
        if "status_confronto" not in colunas_pedido:
            op.execute(
                "ALTER TABLE pedidos_compra ADD COLUMN IF NOT EXISTS status_confronto VARCHAR(30)"
            )
        if "resumo_confronto" not in colunas_pedido:
            op.execute(
                "ALTER TABLE pedidos_compra ADD COLUMN IF NOT EXISTS resumo_confronto TEXT"
            )
        if "confronto_finalizado" not in colunas_pedido:
            op.execute(
                "ALTER TABLE pedidos_compra "
                "ADD COLUMN IF NOT EXISTS confronto_finalizado BOOLEAN DEFAULT FALSE"
            )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_pedidos_compra_nota_entrada_id "
            "ON pedidos_compra (nota_entrada_id)"
        )

    if not inspector.has_table("pedidos_compra_notas_entrada"):
        op.create_table(
            "pedidos_compra_notas_entrada",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("pedido_compra_id", sa.Integer(), nullable=False),
            sa.Column("nota_entrada_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["pedido_compra_id"], ["pedidos_compra.id"]),
            sa.ForeignKeyConstraint(["nota_entrada_id"], ["notas_entrada.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "tenant_id",
                "pedido_compra_id",
                "nota_entrada_id",
                name="uq_pedido_compra_nota_entrada",
            ),
        )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_compra_notas_entrada_id "
        "ON pedidos_compra_notas_entrada (id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_compra_notas_entrada_tenant_id "
        "ON pedidos_compra_notas_entrada (tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_compra_notas_entrada_pedido_compra_id "
        "ON pedidos_compra_notas_entrada (pedido_compra_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_compra_notas_entrada_nota_entrada_id "
        "ON pedidos_compra_notas_entrada (nota_entrada_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pedidos_compra_notas_entrada_user_id "
        "ON pedidos_compra_notas_entrada (user_id)"
    )

    op.execute(
        """
        INSERT INTO pedidos_compra_notas_entrada
            (tenant_id, pedido_compra_id, nota_entrada_id, user_id, created_at, updated_at)
        SELECT DISTINCT
            pc.tenant_id,
            pc.id,
            pc.nota_entrada_id,
            pc.user_id,
            COALESCE(pc.data_confronto, now()),
            now()
        FROM pedidos_compra AS pc
        WHERE pc.nota_entrada_id IS NOT NULL
        ON CONFLICT ON CONSTRAINT uq_pedido_compra_nota_entrada DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_pedidos_compra_notas_entrada_user_id"),
        table_name="pedidos_compra_notas_entrada",
    )
    op.drop_index(
        op.f("ix_pedidos_compra_notas_entrada_nota_entrada_id"),
        table_name="pedidos_compra_notas_entrada",
    )
    op.drop_index(
        op.f("ix_pedidos_compra_notas_entrada_pedido_compra_id"),
        table_name="pedidos_compra_notas_entrada",
    )
    op.drop_index(
        op.f("ix_pedidos_compra_notas_entrada_tenant_id"),
        table_name="pedidos_compra_notas_entrada",
    )
    op.drop_index(
        op.f("ix_pedidos_compra_notas_entrada_id"),
        table_name="pedidos_compra_notas_entrada",
    )
    op.drop_table("pedidos_compra_notas_entrada")
