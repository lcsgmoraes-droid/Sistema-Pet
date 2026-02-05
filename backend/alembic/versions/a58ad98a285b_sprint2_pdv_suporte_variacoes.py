"""sprint2_pdv_suporte_variacoes

Revision ID: a58ad98a285b
Revises: 113a895a867d
Create Date: 2026-01-26 13:37:19.083153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a58ad98a285b'
down_revision: Union[str, Sequence[str], None] = '113a895a867d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1️⃣ Adicionar product_variation_id nos itens de venda
    op.add_column(
        "venda_itens",
        sa.Column(
            "product_variation_id",
            sa.Integer(),
            nullable=True
        )
    )

    # 2️⃣ FK para product_variations
    op.create_foreign_key(
        "fk_venda_itens_variation",
        "venda_itens",
        "product_variations",
        ["product_variation_id"],
        ["id"],
        ondelete="RESTRICT"
    )

    # 3️⃣ Constraint XOR (produto OU variação)
    op.create_check_constraint(
        "ck_venda_itens_produto_ou_variacao",
        "venda_itens",
        "(produto_id IS NOT NULL AND product_variation_id IS NULL) "
        "OR (produto_id IS NULL AND product_variation_id IS NOT NULL)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_venda_itens_produto_ou_variacao", "venda_itens", type_="check")
    op.drop_constraint("fk_venda_itens_variation", "venda_itens", type_="foreignkey")
    op.drop_column("venda_itens", "product_variation_id")
