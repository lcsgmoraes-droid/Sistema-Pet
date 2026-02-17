"""create controle_processamento_mensal

Revision ID: 20260131_controle_processamento
Revises: 20260129_dre_plano_contas
Create Date: 2026-01-31 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260131_controle_processamento'
down_revision: Union[str, Sequence[str], None] = '20260129_dre_plano_contas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria tabela de controle de processamento mensal para provisões"""
    
    op.create_table(
        'controle_processamento_mensal',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String, nullable=False),
        sa.Column('tipo', sa.String(50), nullable=False),
        sa.Column('mes', sa.Integer, nullable=False),
        sa.Column('ano', sa.Integer, nullable=False),
        sa.Column('processado_em', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Índice para garantir unicidade e melhorar performance
    op.create_index(
        'idx_controle_processamento_tenant_tipo_periodo',
        'controle_processamento_mensal',
        ['tenant_id', 'tipo', 'mes', 'ano'],
        unique=True
    )


def downgrade() -> None:
    """Remove tabela de controle de processamento mensal"""
    
    op.drop_index(
        'idx_controle_processamento_tenant_tipo_periodo',
        table_name='controle_processamento_mensal'
    )
    op.drop_table('controle_processamento_mensal')
