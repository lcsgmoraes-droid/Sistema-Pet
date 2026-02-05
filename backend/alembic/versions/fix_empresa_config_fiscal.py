"""Revision ID: fix_empresa_config_fiscal
Revises: 
Create Date: 2026-01-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fix_empresa_config_fiscal_uuid_001'
down_revision = '18d477dfc884'  # última migration
branch_labels = None
depends_on = None


def upgrade():
    # Dropar tabela antiga empresa_config_fiscal se existir
    op.execute('DROP TABLE IF EXISTS empresa_config_fiscal CASCADE')
    
    # Recriar tabela com UUID para tenant_id
    op.create_table(
        'empresa_config_fiscal',
        sa.Column('id', sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fiscal_estado_padrao_id', sa.Integer(), nullable=True),
        sa.Column('uf', sa.String(length=2), nullable=False),
        sa.Column('regime_tributario', sa.String(length=50), nullable=False),
        sa.Column('cnae_principal', sa.String(length=10), nullable=True),
        sa.Column('contribuinte_icms', sa.Boolean(), nullable=False),
        sa.Column('icms_aliquota_interna', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('icms_aliquota_interestadual', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('aplica_difal', sa.Boolean(), nullable=False),
        sa.Column('cfop_venda_interna', sa.String(length=4), nullable=False),
        sa.Column('cfop_venda_interestadual', sa.String(length=4), nullable=False),
        sa.Column('cfop_compra', sa.String(length=4), nullable=False),
        sa.Column('pis_cst_padrao', sa.String(length=3), nullable=True),
        sa.Column('pis_aliquota', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('cofins_cst_padrao', sa.String(length=3), nullable=True),
        sa.Column('cofins_aliquota', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('municipio_iss', sa.String(length=100), nullable=True),
        sa.Column('iss_aliquota', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('iss_retido', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('herdado_do_estado', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_empresa_config_fiscal_tenant_id', 'empresa_config_fiscal', ['tenant_id'])


def downgrade():
    op.drop_index('ix_empresa_config_fiscal_tenant_id', table_name='empresa_config_fiscal')
    op.drop_table('empresa_config_fiscal')
