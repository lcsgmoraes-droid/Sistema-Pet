"""add_tenant_to_payment_tables

Revision ID: 31c2dae52880
Revises: 20260128_nota_tenant
Create Date: 2026-01-27 15:36:39.419640

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31c2dae52880'
down_revision: Union[str, Sequence[str], None] = '20260128_nota_tenant'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona tenant_id às tabelas formas_pagamento_taxas e email_envios"""
    from sqlalchemy.dialects.postgresql import UUID
    
    # 1. formas_pagamento_taxas
    op.add_column('formas_pagamento_taxas', sa.Column(
        'tenant_id',
        UUID(as_uuid=True),
        nullable=False
    ))
    
    op.create_foreign_key(
        'fk_formas_pagamento_taxas_tenant',
        'formas_pagamento_taxas', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    
    op.create_index(
        'ix_formas_pagamento_taxas_tenant_id',
        'formas_pagamento_taxas',
        ['tenant_id']
    )
    
    # 2. email_envios
    op.add_column('email_envios', sa.Column(
        'tenant_id',
        UUID(as_uuid=True),
        nullable=False
    ))
    
    op.create_foreign_key(
        'fk_email_envios_tenant',
        'email_envios', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    
    op.create_index(
        'ix_email_envios_tenant_id',
        'email_envios',
        ['tenant_id']
    )
    
    print("✅ formas_pagamento_taxas e email_envios agora isolados por tenant")


def downgrade() -> None:
    """Remove tenant_id das tabelas"""
    op.drop_index('ix_email_envios_tenant_id')
    op.drop_constraint('fk_email_envios_tenant', 'email_envios', type_='foreignkey')
    op.drop_column('email_envios', 'tenant_id')
    
    op.drop_index('ix_formas_pagamento_taxas_tenant_id')
    op.drop_constraint('fk_formas_pagamento_taxas_tenant', 'formas_pagamento_taxas', type_='foreignkey')
    op.drop_column('formas_pagamento_taxas', 'tenant_id')

