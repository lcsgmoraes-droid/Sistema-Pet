"""create stone tables (stone_transactions, stone_transaction_logs, stone_configs)

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b0c1d2e3f4a5'
down_revision: Union[str, None] = 'a9b0c1d2e3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── stone_transactions ──────────────────────────────────────────────────
    op.create_table(
        'stone_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),

        # IDs de referência
        sa.Column('stone_payment_id', sa.String(100), nullable=False),
        sa.Column('external_id', sa.String(100), nullable=False),

        # FK para vendas / contas a receber
        sa.Column('venda_id', sa.Integer(), sa.ForeignKey('vendas.id'), nullable=True),
        sa.Column('conta_receber_id', sa.Integer(), sa.ForeignKey('contas_receber.id'), nullable=True),

        # Dados do pagamento
        sa.Column('payment_method', sa.String(20), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('installments', sa.Integer(), nullable=True, server_default='1'),

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

        # Taxas
        sa.Column('fee_amount', sa.Numeric(15, 2), nullable=True, server_default='0'),
        sa.Column('net_amount', sa.Numeric(15, 2), nullable=True),

        # Datas
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('refunded_at', sa.DateTime(), nullable=True),
        sa.Column('settlement_date', sa.DateTime(), nullable=True),

        # Webhook
        sa.Column('last_webhook_at', sa.DateTime(), nullable=True),
        sa.Column('webhook_count', sa.Integer(), nullable=True, server_default='0'),

        # JSON completo
        sa.Column('stone_response', postgresql.JSON(astext_type=sa.Text()), nullable=True),

        # Controle de erro
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'),

        # Auditoria
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stone_transactions_id', 'stone_transactions', ['id'])
    op.create_index('ix_stone_transactions_stone_payment_id', 'stone_transactions', ['stone_payment_id'], unique=True)
    op.create_index('ix_stone_transactions_external_id', 'stone_transactions', ['external_id'], unique=True)
    op.create_index('ix_stone_transactions_status', 'stone_transactions', ['status'])
    op.create_index('ix_stone_transactions_venda_id', 'stone_transactions', ['venda_id'])
    op.create_index('ix_stone_transactions_created_at', 'stone_transactions', ['created_at'])
    op.create_index('ix_stone_transactions_tenant_id', 'stone_transactions', ['tenant_id'])

    # ── stone_transaction_logs ──────────────────────────────────────────────
    op.create_table(
        'stone_transaction_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column('transaction_id', sa.Integer(), sa.ForeignKey('stone_transactions.id'), nullable=False),

        # Tipo de evento
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_source', sa.String(30), nullable=True),

        # Dados
        sa.Column('old_status', sa.String(30), nullable=True),
        sa.Column('new_status', sa.String(30), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('webhook_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),

        # IP e user agent
        sa.Column('source_ip', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),

        # Auditoria
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stone_transaction_logs_id', 'stone_transaction_logs', ['id'])
    op.create_index('ix_stone_transaction_logs_transaction_id', 'stone_transaction_logs', ['transaction_id'])
    op.create_index('ix_stone_transaction_logs_created_at', 'stone_transaction_logs', ['created_at'])
    op.create_index('ix_stone_transaction_logs_tenant_id', 'stone_transaction_logs', ['tenant_id'])

    # ── stone_configs ───────────────────────────────────────────────────────
    op.create_table(
        'stone_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Credenciais
        sa.Column('client_id', sa.String(200), nullable=False),
        sa.Column('client_secret', sa.String(200), nullable=False),
        sa.Column('merchant_id', sa.String(200), nullable=False),
        sa.Column('webhook_secret', sa.String(200), nullable=True),

        # Ambiente
        sa.Column('sandbox', sa.Boolean(), nullable=True, server_default='true'),

        # Configurações de pagamento
        sa.Column('enable_pix', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('enable_credit_card', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('enable_debit_card', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('max_installments', sa.Integer(), nullable=True, server_default='12'),

        # Webhook
        sa.Column('webhook_url', sa.String(500), nullable=True),
        sa.Column('webhook_enabled', sa.Boolean(), nullable=True, server_default='true'),

        # Status
        sa.Column('active', sa.Boolean(), nullable=True, server_default='true'),

        # Auditoria
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stone_configs_id', 'stone_configs', ['id'])
    op.create_index('ix_stone_configs_tenant_id', 'stone_configs', ['tenant_id'])


def downgrade() -> None:
    op.drop_table('stone_configs')
    op.drop_table('stone_transaction_logs')
    op.drop_table('stone_transactions')
