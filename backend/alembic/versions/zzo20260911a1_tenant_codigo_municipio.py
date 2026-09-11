"""Adiciona o codigo IBGE do municipio ao cadastro da empresa.

Revision ID: zzo20260911a1
Revises: zzn20260909a1
Create Date: 2026-09-11
"""

from alembic import op
import sqlalchemy as sa

revision = "zzo20260911a1"
down_revision = "zzn20260909a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tenants", sa.Column("codigo_municipio", sa.String(7), nullable=True))


def downgrade():
    op.drop_column("tenants", "codigo_municipio")
