"""Add company master data to tenants table

Revision ID: add_company_data_001
Revises: fix_empresa_config_fiscal_uuid_001
Create Date: 2026-01-31

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_company_data_001'
down_revision = 'fix_empresa_config_fiscal_uuid_001'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar campos de dados cadastrais da empresa
    op.add_column('tenants', sa.Column('razao_social', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('cnpj', sa.String(length=18), nullable=True))
    op.add_column('tenants', sa.Column('inscricao_estadual', sa.String(length=50), nullable=True))
    op.add_column('tenants', sa.Column('inscricao_municipal', sa.String(length=50), nullable=True))
    
    # Campos de endereço
    op.add_column('tenants', sa.Column('endereco', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('numero', sa.String(length=20), nullable=True))
    op.add_column('tenants', sa.Column('complemento', sa.String(length=100), nullable=True))
    op.add_column('tenants', sa.Column('bairro', sa.String(length=100), nullable=True))
    op.add_column('tenants', sa.Column('cidade', sa.String(length=100), nullable=True))
    op.add_column('tenants', sa.Column('uf', sa.String(length=2), nullable=True))
    op.add_column('tenants', sa.Column('cep', sa.String(length=10), nullable=True))
    
    # Campos de contato
    op.add_column('tenants', sa.Column('telefone', sa.String(length=20), nullable=True))
    op.add_column('tenants', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('site', sa.String(length=255), nullable=True))
    
    # Logo da empresa
    op.add_column('tenants', sa.Column('logo_url', sa.String(length=500), nullable=True))
    
    # Campo de atualização
    op.add_column('tenants', sa.Column('updated_at', sa.DateTime(timezone=True), 
                                       server_default=sa.text('now()'), nullable=True))


def downgrade():
    op.drop_column('tenants', 'updated_at')
    op.drop_column('tenants', 'logo_url')
    op.drop_column('tenants', 'site')
    op.drop_column('tenants', 'email')
    op.drop_column('tenants', 'telefone')
    op.drop_column('tenants', 'cep')
    op.drop_column('tenants', 'uf')
    op.drop_column('tenants', 'cidade')
    op.drop_column('tenants', 'bairro')
    op.drop_column('tenants', 'complemento')
    op.drop_column('tenants', 'numero')
    op.drop_column('tenants', 'endereco')
    op.drop_column('tenants', 'inscricao_municipal')
    op.drop_column('tenants', 'inscricao_estadual')
    op.drop_column('tenants', 'cnpj')
    op.drop_column('tenants', 'razao_social')
