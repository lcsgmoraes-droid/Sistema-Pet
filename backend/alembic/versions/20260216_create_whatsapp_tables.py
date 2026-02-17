"""create_whatsapp_tables

Revision ID: 20260216_whatsapp
Revises: 20260216_ia_tenant
Create Date: 2026-02-16 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260216_whatsapp'
down_revision = '20260216_ia_tenant'
branch_labels = None
depends_on = None


def upgrade():
    # 1. tenant_whatsapp_config
    op.create_table('tenant_whatsapp_config',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(length=50), server_default='360dialog', nullable=True),
        sa.Column('api_key', sa.Text(), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('webhook_url', sa.Text(), nullable=True),
        sa.Column('webhook_secret', sa.Text(), nullable=True),
        sa.Column('openai_api_key', sa.Text(), nullable=True),
        sa.Column('model_preference', sa.String(length=50), server_default='gpt-4o-mini', nullable=True),
        sa.Column('auto_response_enabled', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('human_handoff_keywords', sa.Text(), nullable=True),
        sa.Column('working_hours_start', sa.Time(), nullable=True),
        sa.Column('working_hours_end', sa.Time(), nullable=True),
        sa.Column('notificacoes_entrega_enabled', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('bot_name', sa.String(length=100), nullable=True),
        sa.Column('greeting_message', sa.Text(), nullable=True),
        sa.Column('tone', sa.String(length=50), server_default='friendly', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tenant_whatsapp_config_tenant_id', 'tenant_whatsapp_config', ['tenant_id'])
    
    # 2. whatsapp_ia_sessions
    op.create_table('whatsapp_ia_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='bot', nullable=True),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('last_intent', sa.String(length=100), nullable=True),
        sa.Column('message_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_message_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_whatsapp_ia_sessions_tenant_id', 'whatsapp_ia_sessions', ['tenant_id'])
    op.create_index('ix_whatsapp_ia_sessions_phone', 'whatsapp_ia_sessions', ['phone_number'])
    
    # 3. whatsapp_agents
    op.create_table('whatsapp_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='offline', nullable=True),
        sa.Column('max_concurrent_chats', sa.Integer(), server_default='5', nullable=True),
        sa.Column('current_chats', sa.Integer(), server_default='0', nullable=True),
        sa.Column('auto_assign', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('receive_notifications', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_whatsapp_agents_tenant_id', 'whatsapp_agents', ['tenant_id'])
    
    # 4. whatsapp_handoffs (FK session_id deve ser String, não UUID)
    op.create_table('whatsapp_handoffs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('customer_name', sa.String(length=200), nullable=True),
        sa.Column('reason', sa.String(length=50), nullable=False),
        sa.Column('reason_details', sa.Text(), nullable=True),
        sa.Column('sentiment_score', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('sentiment_label', sa.String(length=20), nullable=True),
        sa.Column('priority', sa.String(length=20), server_default='medium', nullable=True),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=True),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolution_time_seconds', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('rating_feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['whatsapp_ia_sessions.id'], ),
        sa.ForeignKeyConstraint(['assigned_to'], ['whatsapp_agents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_whatsapp_handoffs_tenant_id', 'whatsapp_handoffs', ['tenant_id'])
    op.create_index('ix_whatsapp_handoffs_status', 'whatsapp_handoffs', ['status'])
    
    # 5. whatsapp_ia_messages
    op.create_table('whatsapp_ia_messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('tipo', sa.String(length=10), nullable=False),
        sa.Column('conteudo', sa.Text(), nullable=False),
        sa.Column('whatsapp_message_id', sa.String(length=255), nullable=True),
        sa.Column('intent_detected', sa.String(length=100), nullable=True),
        sa.Column('model_used', sa.String(length=50), nullable=True),
        sa.Column('tokens_input', sa.Integer(), nullable=True),
        sa.Column('tokens_output', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('message_metadata', sa.Text(), nullable=True),
        sa.Column('sent_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['whatsapp_ia_sessions.id'], ),
        sa.ForeignKeyConstraint(['sent_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_whatsapp_ia_messages_session_id', 'whatsapp_ia_messages', ['session_id'])
    op.create_index('ix_whatsapp_ia_messages_tenant_id', 'whatsapp_ia_messages', ['tenant_id'])
    
    # 6. whatsapp_ia_metrics
    op.create_table('whatsapp_ia_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('metric_metadata', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_whatsapp_ia_metrics_tenant_id', 'whatsapp_ia_metrics', ['tenant_id'])
    op.create_index('ix_whatsapp_ia_metrics_timestamp', 'whatsapp_ia_metrics', ['timestamp'])
    
    # 7. whatsapp_internal_notes (session_id deve ser String, não UUID)
    op.create_table('whatsapp_internal_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('handoff_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('note_type', sa.String(length=50), server_default='general', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['whatsapp_ia_sessions.id'], ),
        sa.ForeignKeyConstraint(['handoff_id'], ['whatsapp_handoffs.id'], ),
        sa.ForeignKeyConstraint(['agent_id'], ['whatsapp_agents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_whatsapp_internal_notes_handoff_id', 'whatsapp_internal_notes', ['handoff_id'])


def downgrade():
    op.drop_table('whatsapp_internal_notes')
    op.drop_table('whatsapp_ia_metrics')
    op.drop_table('whatsapp_ia_messages')
    op.drop_table('whatsapp_handoffs')
    op.drop_table('whatsapp_agents')
    op.drop_table('whatsapp_ia_sessions')
    op.drop_table('tenant_whatsapp_config')
