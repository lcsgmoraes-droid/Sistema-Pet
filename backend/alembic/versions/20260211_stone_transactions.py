"""create stone_transactions table

Revision ID: 20260211_stone_transactions
Revises: 20260211_add_validacao_id, 20260211_add_conciliacao_3_abas
Create Date: 2026-02-11

Cria tabela stone_transactions para evitar erro quando SQLAlchemy
tenta acessar relacionamento com contas_receber
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers
revision = '20260211_stone_transactions'
down_revision = ('20260211_add_validacao_id', '20260211_add_conciliacao_3_abas')
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'stone_transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        
        # IDs de referência
        sa.Column('stone_payment_id', sa.String(100), nullable=False, unique=True),
        sa.Column('external_id', sa.String(100), nullable=False, unique=True),
        
        # Relacionamentos
        sa.Column('venda_id', sa.Integer(), nullable=True),
        sa.Column('conta_receber_id', sa.Integer(), nullable=True),
        
        # Dados do pagamento
        sa.Column('payment_method', sa.String(20), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('installments', sa.Integer(), server_default='1'),
        
        # Status
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('stone_status', sa.String(50), nullable=True),
        
        # Cliente
        sa.Column('customer_name', sa.String(200), nullable=True),
        sa.Column('customer_document', sa.String(20), nullable=True),
        sa.Column('customer_email', sa.String(200), nullable=True),
        
        # PIX
        sa.Column('pix_qr_code', sa.Text(), nullable=True),
        sa.Column('pix_qr_code_url', sa.String(500), nullable=True),
        sa.Column('pix_copy_paste', sa.Text(), nullable=True),
        sa.Column('pix_expiration', sa.DateTime(), nullable=True),
        
        # Cartão
        sa.Column('card_brand', sa.String(20), nullable=True),
        sa.Column('card_last_digits', sa.String(4), nullable=True),
        
        # Financeiro
        sa.Column('fee_amount', sa.Numeric(15, 2), server_default='0'),
        sa.Column('net_amount', sa.Numeric(15, 2), nullable=True),
        
        # Datas
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('refunded_at', sa.DateTime(), nullable=True),
        sa.Column('settlement_date', sa.DateTime(), nullable=True),
        
        # Webhooks
        sa.Column('last_webhook_at', sa.DateTime(), nullable=True),
        sa.Column('webhook_count', sa.Integer(), server_default='0'),
        
        # JSON
        sa.Column('stone_response', JSON(), nullable=True),
        
        # Erros
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        
        # Auditoria
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        
        # Constraints
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar FKs separadamente
    op.create_foreign_key(
        'fk_stone_transactions_tenant',
        'stone_transactions', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_stone_transactions_venda',
        'stone_transactions', 'vendas',
        ['venda_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_stone_transactions_conta_receber',
        'stone_transactions', 'contas_receber',
        ['conta_receber_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_stone_transactions_user',
        'stone_transactions', 'users',
        ['user_id'], ['id'],
        ondelete='RESTRICT'
    )
    
    # Indexes
    op.create_index('ix_stone_transactions_tenant_id', 'stone_transactions', ['tenant_id'])
    op.create_index('ix_stone_transactions_stone_payment_id', 'stone_transactions', ['stone_payment_id'])
    op.create_index('ix_stone_transactions_external_id', 'stone_transactions', ['external_id'])
    op.create_index('ix_stone_transactions_venda_id', 'stone_transactions', ['venda_id'])
    op.create_index('ix_stone_transactions_conta_receber_id', 'stone_transactions', ['conta_receber_id'])
    op.create_index('ix_stone_transactions_status', 'stone_transactions', ['status'])
    op.create_index('ix_stone_transactions_created_at', 'stone_transactions', ['created_at'])


def downgrade():
    op.drop_table('stone_transactions')
