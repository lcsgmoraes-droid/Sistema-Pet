"""add_ecommerce_aparencia_columns

Adiciona colunas de aparencia do e-commerce (logo e banners) na tabela tenants.

Revision ID: a1b2c3d4e5f6
Revises: f6c9a1b2d3e4
Create Date: 2026-02-27 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f6c9a1b2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona colunas banner_1_url, banner_2_url, banner_3_url em tenants."""
    op.add_column('tenants', sa.Column('banner_1_url', sa.String(500), nullable=True))
    op.add_column('tenants', sa.Column('banner_2_url', sa.String(500), nullable=True))
    op.add_column('tenants', sa.Column('banner_3_url', sa.String(500), nullable=True))


def downgrade() -> None:
    """Remove as colunas de banner."""
    op.drop_column('tenants', 'banner_3_url')
    op.drop_column('tenants', 'banner_2_url')
    op.drop_column('tenants', 'banner_1_url')
