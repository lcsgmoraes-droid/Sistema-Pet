"""add departamento_id to categorias

Revision ID: dep001cat2026
Revises: z1a2b3c4d5e6
Create Date: 2026-03-15 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dep001cat2026'
down_revision: Union[str, None] = 'z1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona departamento_id à tabela categorias (opcional, sem FK forçada para não quebrar dados existentes)
    op.execute(
        "ALTER TABLE categorias ADD COLUMN IF NOT EXISTS departamento_id INTEGER REFERENCES departamentos(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.drop_column('categorias', 'departamento_id')
