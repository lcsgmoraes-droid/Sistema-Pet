"""
Migration: Criar tabela de pendências de estoque
Sistema de lista de espera para produtos sem estoque com notificação automática
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade():
    """Criar tabela pendencias_estoque"""
    
    op.create_table(
        'pendencias_estoque',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('produto_id', sa.Integer(), nullable=False),
        sa.Column('usuario_registrou_id', sa.Integer(), nullable=False),
        sa.Column('quantidade_desejada', sa.Float(), nullable=False),
        sa.Column('valor_referencia', sa.Float(), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pendente'),
        sa.Column('data_notificacao', sa.DateTime(), nullable=True),
        sa.Column('whatsapp_enviado', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('mensagem_whatsapp_id', sa.String(100), nullable=True),
        sa.Column('data_finalizacao', sa.DateTime(), nullable=True),
        sa.Column('venda_id', sa.Integer(), nullable=True),
        sa.Column('motivo_cancelamento', sa.Text(), nullable=True),
        sa.Column('prioridade', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('data_registro', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id']),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id']),
        sa.ForeignKeyConstraint(['usuario_registrou_id'], ['users.id']),
        sa.ForeignKeyConstraint(['venda_id'], ['vendas.id'])
    )
    
    # Índices para melhor performance
    op.create_index('ix_pendencias_estoque_tenant_id', 'pendencias_estoque', ['tenant_id'])
    op.create_index('ix_pendencias_estoque_cliente_id', 'pendencias_estoque', ['cliente_id'])
    op.create_index('ix_pendencias_estoque_produto_id', 'pendencias_estoque', ['produto_id'])
    op.create_index('ix_pendencias_estoque_status', 'pendencias_estoque', ['status'])
    op.create_index('ix_pendencias_estoque_data_registro', 'pendencias_estoque', ['data_registro'])
    
    # Índice composto para buscar pendências ativas de um produto
    op.create_index(
        'ix_pendencias_produto_status',
        'pendencias_estoque',
        ['produto_id', 'status']
    )
    
    print("✅ Tabela pendencias_estoque criada com sucesso!")


def downgrade():
    """Remover tabela pendencias_estoque"""
    
    op.drop_index('ix_pendencias_produto_status', table_name='pendencias_estoque')
    op.drop_index('ix_pendencias_estoque_data_registro', table_name='pendencias_estoque')
    op.drop_index('ix_pendencias_estoque_status', table_name='pendencias_estoque')
    op.drop_index('ix_pendencias_estoque_produto_id', table_name='pendencias_estoque')
    op.drop_index('ix_pendencias_estoque_cliente_id', table_name='pendencias_estoque')
    op.drop_index('ix_pendencias_estoque_tenant_id', table_name='pendencias_estoque')
    
    op.drop_table('pendencias_estoque')
    
    print("✅ Tabela pendencias_estoque removida!")
