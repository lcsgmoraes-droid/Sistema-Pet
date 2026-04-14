"""add dre_subcategoria_id to tipo_despesas

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-04-13 21:25:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tipo_despesas
        ADD COLUMN IF NOT EXISTS dre_subcategoria_id INTEGER
        """
    )

    op.execute(
        """
        UPDATE tipo_despesas
        SET dre_subcategoria_id = 2
        WHERE dre_subcategoria_id IS NULL
        """
    )

    op.execute(
        """
        ALTER TABLE tipo_despesas
        ALTER COLUMN dre_subcategoria_id SET NOT NULL
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tipo_despesas_dre_subcategoria_id
        ON tipo_despesas (dre_subcategoria_id)
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_tipo_despesas_dre_subcategoria'
            ) THEN
                ALTER TABLE tipo_despesas
                ADD CONSTRAINT fk_tipo_despesas_dre_subcategoria
                FOREIGN KEY (dre_subcategoria_id)
                REFERENCES dre_subcategorias(id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE tipo_despesas
        DROP CONSTRAINT IF EXISTS fk_tipo_despesas_dre_subcategoria
        """
    )

    op.execute(
        """
        DROP INDEX IF EXISTS ix_tipo_despesas_dre_subcategoria_id
        """
    )

    op.execute(
        """
        ALTER TABLE tipo_despesas
        DROP COLUMN IF EXISTS dre_subcategoria_id
        """
    )
