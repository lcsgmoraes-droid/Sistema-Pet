"""create feature_flags table

Revision ID: 20260127_create_feature_flags
Revises: 20260126_add_updated_at_venda_pagamentos
Create Date: 2026-01-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '20260127_create_feature_flags'
down_revision: Union[str, Sequence[str], None] = '20260126_vpag_upd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Cria tabela feature_flags para controle de funcionalidades por tenant.
    
    Objetivo: Permitir ativar/desativar features como IA de Oportunidades no PDV
    de forma isolada por tenant, garantindo que o sistema nunca dependa de features
    experimentais para funcionar.
    """
    op.create_table(
        'feature_flags',
        sa.Column(
            'id',
            sa.Integer(),
            sa.Identity(always=True),
            nullable=False,
            primary_key=True
        ),
        sa.Column(
            'tenant_id',
            UUID(as_uuid=True),
            nullable=False,
            index=True,
            comment='Tenant proprietário da feature flag'
        ),
        sa.Column(
            'feature_key',
            sa.String(length=100),
            nullable=False,
            index=True,
            comment='Identificador único da feature (ex: PDV_IA_OPORTUNIDADES)'
        ),
        sa.Column(
            'enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='Status da feature: true=ativa, false=desligada'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'feature_key', name='uq_feature_flags_tenant_feature'),
        sa.ForeignKeyConstraint(
            ['tenant_id'],
            ['tenants.id'],
            name='fk_feature_flags_tenant_id'
        )
    )
    
    # Índice composto para otimizar queries de lookup por tenant
    op.create_index(
        'ix_feature_flags_tenant_feature_lookup',
        'feature_flags',
        ['tenant_id', 'feature_key', 'enabled']
    )


def downgrade() -> None:
    """
    Remove tabela feature_flags e seus índices.
    """
    op.drop_index('ix_feature_flags_tenant_feature_lookup', table_name='feature_flags')
    op.drop_table('feature_flags')
