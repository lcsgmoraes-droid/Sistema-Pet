"""sprint2_venda_itens_suporte_variacoes

Revision ID: 6c11cea65dd5
Revises: 32274520dd81
Create Date: 2026-01-26 16:58:17.814907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c11cea65dd5'
down_revision: Union[str, Sequence[str], None] = '32274520dd81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Verificar se a coluna já existe antes de adicionar
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('venda_itens')]
    
    # 1️⃣ Adiciona coluna para variação de produto (se não existir)
    if 'product_variation_id' not in columns:
        op.add_column(
            "venda_itens",
            sa.Column("product_variation_id", sa.Integer(), nullable=True),
        )

    # 2️⃣ Cria FK para product_variations (se não existir)
    fks = [fk['name'] for fk in inspector.get_foreign_keys('venda_itens')]
    if 'fk_venda_itens_product_variation' not in fks:
        op.create_foreign_key(
            "fk_venda_itens_product_variation",
            "venda_itens",
            "product_variations",
            ["product_variation_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # 3️⃣ Constraint XOR (se não existir)
    checks = [chk['name'] for chk in inspector.get_check_constraints('venda_itens')]
    if 'ck_venda_itens_produto_ou_variacao' not in checks:
        op.create_check_constraint(
            "ck_venda_itens_produto_ou_variacao",
            "venda_itens",
            """
            (
                (product_id IS NOT NULL AND product_variation_id IS NULL)
                OR
                (product_id IS NULL AND product_variation_id IS NOT NULL)
            )
            """,
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_venda_itens_produto_ou_variacao",
        "venda_itens",
        type_="check",
    )

    op.drop_constraint(
        "fk_venda_itens_product_variation",
        "venda_itens",
        type_="foreignkey",
    )

    op.drop_column("venda_itens", "product_variation_id")
