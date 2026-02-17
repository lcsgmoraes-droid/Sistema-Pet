"""add_tenant_id_to_comissoes_configuracao

Revision ID: 20260216_comissoes_tenant
Revises: 20260216_comissoes_cfg
Create Date: 2026-02-16 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '20260216_comissoes_tenant'
down_revision: Union[str, Sequence[str], None] = '20260216_comissoes_cfg'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tenant_id column to comissoes_configuracao table."""
    # Add tenant_id column (nullable for backward compatibility)
    op.add_column(
        'comissoes_configuracao',
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True)
    )
    
    # Create index for better performance
    op.create_index(
        'ix_comissoes_configuracao_tenant_id',
        'comissoes_configuracao',
        ['tenant_id']
    )
    
    # Populate tenant_id from funcionario's tenant_id
    op.execute("""
        UPDATE comissoes_configuracao cc
        SET tenant_id = c.tenant_id
        FROM clientes c
        WHERE cc.funcionario_id = c.id
        AND cc.tenant_id IS NULL
    """)


def downgrade() -> None:
    """Remove tenant_id column from comissoes_configuracao table."""
    op.drop_index('ix_comissoes_configuracao_tenant_id', 'comissoes_configuracao')
    op.drop_column('comissoes_configuracao', 'tenant_id')
