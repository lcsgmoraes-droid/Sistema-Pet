"""sprint2_view_listagem_produtos

Revision ID: c49bb738adec
Revises: a58ad98a285b
Create Date: 2026-01-26 13:41:00.356893

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c49bb738adec'
down_revision: Union[str, Sequence[str], None] = 'a58ad98a285b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE OR REPLACE VIEW vw_produtos_listagem AS

        -- Produtos simples e pais
        SELECT
            p.id                AS id,
            p.user_id           AS user_id,
            p.nome              AS nome,
            p.is_parent         AS is_parent,
            p.is_sellable       AS is_sellable,
            NULL::INTEGER       AS parent_id,
            NULL::INTEGER       AS variation_id,
            'PRODUTO'           AS tipo
        FROM produtos p

        UNION ALL

        -- Variações
        SELECT
            pv.id               AS id,
            NULL::INTEGER       AS user_id,
            pv.name             AS nome,
            FALSE               AS is_parent,
            TRUE                AS is_sellable,
            pv.product_parent_id AS parent_id,
            pv.id               AS variation_id,
            'VARIACAO'          AS tipo
        FROM product_variations pv
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP VIEW IF EXISTS vw_produtos_listagem")
