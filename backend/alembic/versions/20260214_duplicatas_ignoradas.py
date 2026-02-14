"""add_duplicatas_ignoradas_table

Revision ID: 20260214_duplicatas_ignoradas
Revises: dae0f14c89a2
Create Date: 2026-02-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260214_duplicatas_ignoradas'
down_revision = '20260212_fix_historico_timestamps'
branch_labels = None
depends_on = None


def upgrade():
    # Criar tabela duplicatas_ignoradas
    op.create_table(
        'duplicatas_ignoradas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('produto_id_1', sa.Integer(), nullable=False),
        sa.Column('produto_id_2', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('data_ignorado', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['produto_id_1'], ['produtos.id'], ),
        sa.ForeignKeyConstraint(['produto_id_2'], ['produtos.id'], ),
        sa.ForeignKeyConstraint(['usuario_id'], ['users.id'], ),
        sa.UniqueConstraint('tenant_id', 'produto_id_1', 'produto_id_2', name='uq_duplicata_ignorada')
    )
    
    # Criar índices
    op.create_index(op.f('ix_duplicatas_ignoradas_id'), 'duplicatas_ignoradas', ['id'], unique=False)
    op.create_index(op.f('ix_duplicatas_ignoradas_tenant_id'), 'duplicatas_ignoradas', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_duplicatas_ignoradas_produto_id_1'), 'duplicatas_ignoradas', ['produto_id_1'], unique=False)
    op.create_index(op.f('ix_duplicatas_ignoradas_produto_id_2'), 'duplicatas_ignoradas', ['produto_id_2'], unique=False)


def downgrade():
    # Remover índices
    op.drop_index(op.f('ix_duplicatas_ignoradas_produto_id_2'), table_name='duplicatas_ignoradas')
    op.drop_index(op.f('ix_duplicatas_ignoradas_produto_id_1'), table_name='duplicatas_ignoradas')
    op.drop_index(op.f('ix_duplicatas_ignoradas_tenant_id'), table_name='duplicatas_ignoradas')
    op.drop_index(op.f('ix_duplicatas_ignoradas_id'), table_name='duplicatas_ignoradas')
    
    # Remover tabela
    op.drop_table('duplicatas_ignoradas')
