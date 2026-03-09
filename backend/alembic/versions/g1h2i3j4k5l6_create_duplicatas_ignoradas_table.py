"""create duplicatas_ignoradas table

Revision ID: g1h2i3j4k5l6
Revises: f7a8b9c0d1e2
Create Date: 2026-03-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('duplicatas_ignoradas'):
        op.create_table(
            'duplicatas_ignoradas',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
            sa.Column('produto_id_1', sa.Integer(), sa.ForeignKey('produtos.id'), nullable=False, index=True),
            sa.Column('produto_id_2', sa.Integer(), sa.ForeignKey('produtos.id'), nullable=False, index=True),
            sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('data_ignorado', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint('tenant_id', 'produto_id_1', 'produto_id_2', name='uq_duplicata_ignorada'),
        )


def downgrade() -> None:
    op.drop_table('duplicatas_ignoradas')
