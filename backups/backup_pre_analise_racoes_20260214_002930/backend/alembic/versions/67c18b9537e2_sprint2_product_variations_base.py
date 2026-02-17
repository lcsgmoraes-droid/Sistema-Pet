"""sprint2_product_variations_base

Revision ID: 67c18b9537e2
Revises: efc4e939587f
Create Date: 2026-01-26 13:23:31.257006

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67c18b9537e2'
down_revision: Union[str, Sequence[str], None] = 'efc4e939587f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Evolução da tabela products
    op.add_column(
        "produtos",
        sa.Column(
            "is_parent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "produtos",
        sa.Column(
            "is_sellable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    # Nova tabela product_variations
    op.create_table(
        "product_variations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False, index=True),
        sa.Column("product_parent_id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["product_parent_id"],
            ["produtos.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_product_variations_parent",
        "product_variations",
        ["product_parent_id"],
    )

    op.create_unique_constraint(
        "uq_product_variations_tenant_sku",
        "product_variations",
        ["tenant_id", "sku"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_product_variations_tenant_sku", "product_variations", type_="unique")
    op.drop_index("ix_product_variations_parent", table_name="product_variations")
    op.drop_table("product_variations")

    op.drop_column("produtos", "is_sellable")
    op.drop_column("produtos", "is_parent")
