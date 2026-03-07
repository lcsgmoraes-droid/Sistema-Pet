"""add stone connect and conciliacao fields to stone_configs

Revision ID: i2j3k4l5m6n7
Revises: h1b2c3d4e5f6
Create Date: 2026-03-06

Adiciona colunas à tabela stone_configs para suportar:
  - Stone Connect (Pagar.me): merchant_id agora nullable, sandbox default false
  - Stone Conciliação API: client_id/secret específicos, affiliation_code, documento, username/password
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'i2j3k4l5m6n7'
down_revision: Union[str, None] = 'h1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # merchant_id não é obrigatório no Pagar.me Connect
    op.alter_column('stone_configs', 'merchant_id', nullable=True)

    # Campos para Stone Conciliação
    op.add_column('stone_configs', sa.Column('conciliacao_client_id', sa.String(200), nullable=True))
    op.add_column('stone_configs', sa.Column('conciliacao_client_secret', sa.String(200), nullable=True))
    op.add_column('stone_configs', sa.Column('affiliation_code', sa.String(100), nullable=True))
    op.add_column('stone_configs', sa.Column('documento', sa.String(20), nullable=True))
    op.add_column('stone_configs', sa.Column('conciliacao_username', sa.String(200), nullable=True))
    op.add_column('stone_configs', sa.Column('conciliacao_password_enc', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('stone_configs', 'conciliacao_password_enc')
    op.drop_column('stone_configs', 'conciliacao_username')
    op.drop_column('stone_configs', 'documento')
    op.drop_column('stone_configs', 'affiliation_code')
    op.drop_column('stone_configs', 'conciliacao_client_secret')
    op.drop_column('stone_configs', 'conciliacao_client_id')
    op.alter_column('stone_configs', 'merchant_id', nullable=False)
