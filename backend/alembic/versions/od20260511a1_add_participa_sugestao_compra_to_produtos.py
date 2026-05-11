"""add participa_sugestao_compra to produtos

Revision ID: od20260511a1
Revises: oc20260509a1
Create Date: 2026-05-11 20:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "od20260511a1"
down_revision = "oc20260509a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE produtos
        ADD COLUMN IF NOT EXISTS participa_sugestao_compra BOOLEAN NOT NULL DEFAULT TRUE
        """
    )
    op.execute(
        """
        UPDATE produtos
        SET participa_sugestao_compra = FALSE
        WHERE COALESCE(e_granel, FALSE) IS TRUE
           OR LOWER(COALESCE(nome, '')) LIKE '%granel%'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE produtos
        DROP COLUMN IF EXISTS participa_sugestao_compra
        """
    )
