"""create_opcoes_racao

Revision ID: 20260214_opcoes_racao
Revises: 20260214_add_racao_ai_fields
Create Date: 2026-02-14 04:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260214_opcoes_racao'
down_revision = 'dae0f14c89a2'  # Revisa para a migration anterior
branch_labels = None
depends_on = None


def upgrade():
    # Tabela de Linhas de Ração (Premium, Super Premium, etc.)
    op.create_table(
        'linhas_racao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True, default=0),
        sa.Column('ativo', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_linhas_racao_tenant_id', 'linhas_racao', ['tenant_id'])
    op.create_index('ix_linhas_racao_nome', 'linhas_racao', ['nome'])
    
    # Tabela de Portes de Animal
    op.create_table(
        'portes_animal',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True, default=0),
        sa.Column('ativo', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_portes_animal_tenant_id', 'portes_animal', ['tenant_id'])
    op.create_index('ix_portes_animal_nome', 'portes_animal', ['nome'])
    
    # Tabela de Fases/Público
    op.create_table(
        'fases_publico',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True, default=0),
        sa.Column('ativo', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_fases_publico_tenant_id', 'fases_publico', ['tenant_id'])
    op.create_index('ix_fases_publico_nome', 'fases_publico', ['nome'])
    
    # Tabela de Tipos de Tratamento
    op.create_table(
        'tipos_tratamento',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True, default=0),
        sa.Column('ativo', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_tipos_tratamento_tenant_id', 'tipos_tratamento', ['tenant_id'])
    op.create_index('ix_tipos_tratamento_nome', 'tipos_tratamento', ['nome'])
    
    # Tabela de Sabores/Proteínas
    op.create_table(
        'sabores_proteina',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True, default=0),
        sa.Column('ativo', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_sabores_proteina_tenant_id', 'sabores_proteina', ['tenant_id'])
    op.create_index('ix_sabores_proteina_nome', 'sabores_proteina', ['nome'])
    
    # Tabela de Apresentações (Pesos)
    op.create_table(
        'apresentacoes_peso',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('peso_kg', sa.Float(), nullable=False),
        sa.Column('descricao', sa.String(100), nullable=True),  # Ex: "15kg", "10.1kg", "1kg"
        sa.Column('ordem', sa.Integer(), nullable=True, default=0),
        sa.Column('ativo', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_apresentacoes_peso_tenant_id', 'apresentacoes_peso', ['tenant_id'])
    op.create_index('ix_apresentacoes_peso_peso_kg', 'apresentacoes_peso', ['peso_kg'])


def downgrade():
    op.drop_index('ix_apresentacoes_peso_peso_kg', table_name='apresentacoes_peso')
    op.drop_index('ix_apresentacoes_peso_tenant_id', table_name='apresentacoes_peso')
    op.drop_table('apresentacoes_peso')
    
    op.drop_index('ix_sabores_proteina_nome', table_name='sabores_proteina')
    op.drop_index('ix_sabores_proteina_tenant_id', table_name='sabores_proteina')
    op.drop_table('sabores_proteina')
    
    op.drop_index('ix_tipos_tratamento_nome', table_name='tipos_tratamento')
    op.drop_index('ix_tipos_tratamento_tenant_id', table_name='tipos_tratamento')
    op.drop_table('tipos_tratamento')
    
    op.drop_index('ix_fases_publico_nome', table_name='fases_publico')
    op.drop_index('ix_fases_publico_tenant_id', table_name='fases_publico')
    op.drop_table('fases_publico')
    
    op.drop_index('ix_portes_animal_nome', table_name='portes_animal')
    op.drop_index('ix_portes_animal_tenant_id', table_name='portes_animal')
    op.drop_table('portes_animal')
    
    op.drop_index('ix_linhas_racao_nome', table_name='linhas_racao')
    op.drop_index('ix_linhas_racao_tenant_id', table_name='linhas_racao')
    op.drop_table('linhas_racao')
