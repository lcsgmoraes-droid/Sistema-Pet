"""indexa a listagem paginada de notas de entrada

Revision ID: zwm20260724a1
Revises: zwl20260723a1
Create Date: 2026-07-24
"""

from alembic import op

revision = "zwm20260724a1"
down_revision = "zwl20260723a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_notas_entrada_tenant_data_entrada",
        "notas_entrada",
        ["tenant_id", "data_entrada"],
        unique=False,
    )
    op.create_index(
        "ix_notas_entrada_tenant_status_data_entrada",
        "notas_entrada",
        ["tenant_id", "status", "data_entrada"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notas_entrada_tenant_status_data_entrada",
        table_name="notas_entrada",
    )
    op.drop_index(
        "ix_notas_entrada_tenant_data_entrada",
        table_name="notas_entrada",
    )
