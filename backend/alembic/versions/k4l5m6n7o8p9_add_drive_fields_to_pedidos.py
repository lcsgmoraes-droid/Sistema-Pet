"""add drive fields to pedidos

Revision ID: k4l5m6n7o8p9
Revises: j3k4l5m6n7o8
Create Date: 2026-03-08

Adiciona campos de Drive-Thru pickup na tabela pedidos:
- is_drive: se o pedido é retirada em modo drive (cliente no carro)
- drive_chegou_at: quando o cliente avisou que chegou
- drive_entregue_at: quando o funcionário confirmou entrega no carro
"""
from alembic import op
import sqlalchemy as sa


revision = 'k4l5m6n7o8p9'
down_revision = 'j3k4l5m6n7o8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('pedidos', sa.Column('is_drive', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('pedidos', sa.Column('drive_chegou_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('pedidos', sa.Column('drive_entregue_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('pedidos', 'drive_entregue_at')
    op.drop_column('pedidos', 'drive_chegou_at')
    op.drop_column('pedidos', 'is_drive')
