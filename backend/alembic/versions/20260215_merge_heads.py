"""merge_multiple_heads_20260215

Revision ID: 20260215_merge_heads
Revises: 20260215_create_pendencias_estoque, 20260215_add_tenant_id_to_pedidos_compra_itens
Create Date: 2026-02-15 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260215_merge_heads'
down_revision: Union[str, Sequence[str], None] = ('20260215_create_pendencias_estoque', '20260215_add_tenant_id_to_pedidos_compra_itens')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge multiple heads. No database changes needed."""
    pass


def downgrade() -> None:
    """Merge downgrade. No database changes needed."""
    pass
