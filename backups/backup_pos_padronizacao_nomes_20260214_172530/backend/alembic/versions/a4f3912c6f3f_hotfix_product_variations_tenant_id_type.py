"""hotfix_product_variations_tenant_id_type

Revision ID: a4f3912c6f3f
Revises: c49bb738adec
Create Date: 2026-01-26 13:52:21.152657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a4f3912c6f3f'
down_revision: Union[str, Sequence[str], None] = 'c49bb738adec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Primeiro, remover dados existentes se houver (tabela vazia do sprint 2)
    op.execute("DELETE FROM product_variations")
    
    # Alterar tenant_id de Integer para UUID usando USING clause
    op.execute("""
        ALTER TABLE product_variations 
        ALTER COLUMN tenant_id TYPE UUID 
        USING tenant_id::text::uuid
    """)
    
    # Adicionar FK constraint para tenants.id
    op.create_foreign_key(
        'fk_product_variations_tenant',
        'product_variations',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_product_variations_tenant', 'product_variations', type_='foreignkey')
    op.alter_column(
        'product_variations',
        'tenant_id',
        type_=sa.Integer(),
        existing_type=UUID(as_uuid=True),
        existing_nullable=False
    )
