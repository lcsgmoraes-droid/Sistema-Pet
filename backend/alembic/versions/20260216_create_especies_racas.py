"""create_especies_and_racas_tables

Revision ID: 20260216_especies_racas
Revises: 20260216_fix_paradas
Create Date: 2026-02-16 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '20260216_especies_racas'
down_revision: Union[str, Sequence[str], None] = '20260216_fix_paradas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create especies and racas tables."""
    
    # Get connection and inspector to check existing tables
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create especies table only if it doesn't exist
    if 'especies' not in existing_tables:
        op.create_table(
            'especies',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nome', sa.String(100), nullable=False),
            sa.Column('ativo', sa.Boolean(), nullable=True, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for especies
        op.create_index('ix_especies_id', 'especies', ['id'])
        op.create_index('ix_especies_nome', 'especies', ['nome'])
        op.create_index('ix_especies_tenant_id', 'especies', ['tenant_id'])
    
    # Create racas table only if it doesn't exist
    if 'racas' not in existing_tables:
        op.create_table(
            'racas',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nome', sa.String(100), nullable=False),
            sa.Column('especie_id', sa.Integer(), nullable=False),
            sa.Column('ativo', sa.Boolean(), nullable=True, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('tenant_id', UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for racas
        op.create_index('ix_racas_id', 'racas', ['id'])
        op.create_index('ix_racas_nome', 'racas', ['nome'])
        op.create_index('ix_racas_especie_id', 'racas', ['especie_id'])
        op.create_index('ix_racas_tenant_id', 'racas', ['tenant_id'])
        
        # Create foreign key for racas.especie_id
        op.create_foreign_key(
            'fk_racas_especie',
            'racas', 'especies',
            ['especie_id'], ['id'],
            ondelete='CASCADE'
        )


def downgrade() -> None:
    """Drop especies and racas tables."""
    op.drop_constraint('fk_racas_especie', 'racas', type_='foreignkey')
    
    op.drop_index('ix_racas_tenant_id', 'racas')
    op.drop_index('ix_racas_especie_id', 'racas')
    op.drop_index('ix_racas_nome', 'racas')
    op.drop_index('ix_racas_id', 'racas')
    op.drop_table('racas')
    
    op.drop_index('ix_especies_tenant_id', 'especies')
    op.drop_index('ix_especies_nome', 'especies')
    op.drop_index('ix_especies_id', 'especies')
    op.drop_table('especies')
