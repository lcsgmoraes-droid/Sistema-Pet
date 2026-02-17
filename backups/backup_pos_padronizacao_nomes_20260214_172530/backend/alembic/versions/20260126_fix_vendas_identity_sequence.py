"""fix vendas.id identity sequence restart

Revision ID: 20260126_fix_seq
Revises: 20260126_identity
Create Date: 2026-01-26 15:10:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260126_fix_seq'
down_revision = '20260126_identity'
branch_labels = None
depends_on = None


def upgrade():
    """
    Reinicia a sequence da IDENTITY com o valor correto
    """
    # Obtém o maior ID e reinicia a sequence
    op.execute("""
        DO $$
        DECLARE
            max_id INTEGER;
        BEGIN
            SELECT COALESCE(MAX(id), 0) INTO max_id FROM vendas;
            EXECUTE format('ALTER TABLE vendas ALTER COLUMN id RESTART WITH %s', max_id + 1);
        END $$;
    """)


def downgrade():
    """
    Não faz nada no downgrade
    """
    pass
