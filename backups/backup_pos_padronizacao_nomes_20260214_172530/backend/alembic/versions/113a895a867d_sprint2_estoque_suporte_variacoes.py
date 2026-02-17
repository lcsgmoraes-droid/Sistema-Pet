"""sprint2_estoque_suporte_variacoes

Revision ID: 113a895a867d
Revises: 67c18b9537e2
Create Date: 2026-01-26 13:31:29.049407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '113a895a867d'
down_revision: Union[str, Sequence[str], None] = '67c18b9537e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1️⃣ Adicionar coluna product_variation_id em estoque/lotes
    op.add_column(
        "produto_lotes",
        sa.Column(
            "product_variation_id",
            sa.Integer(),
            nullable=True
        )
    )

    # 2️⃣ Foreign key para product_variations
    op.create_foreign_key(
        "fk_produto_lotes_variation",
        "produto_lotes",
        "product_variations",
        ["product_variation_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # 3️⃣ Constraint: produto_id XOR product_variation_id
    op.create_check_constraint(
        "ck_produto_lotes_produto_ou_variacao",
        "produto_lotes",
        "(produto_id IS NOT NULL AND product_variation_id IS NULL) "
        "OR (produto_id IS NULL AND product_variation_id IS NOT NULL)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_produto_lotes_produto_ou_variacao", "produto_lotes", type_="check")
    op.drop_constraint("fk_produto_lotes_variation", "produto_lotes", type_="foreignkey")
    op.drop_column("produto_lotes", "product_variation_id")
