"""add pos_serial_number to stone_configs

Revision ID: p1q2r3s4t5u6
Revises: i2j3k4l5m6n7
Create Date: 2026-05-31

Adiciona coluna pos_serial_number à tabela stone_configs para armazenar
o número de série da maquininha POS principal do tenant.
"""

from alembic import op
import sqlalchemy as sa

revision = 'p1q2r3s4t5u6'
down_revision = 'i2j3k4l5m6n7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'stone_configs',
        sa.Column('pos_serial_number', sa.String(50), nullable=True)
    )


def downgrade():
    op.drop_column('stone_configs', 'pos_serial_number')
