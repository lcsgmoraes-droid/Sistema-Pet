"""add gateway financials to venda pagamentos

Revision ID: pf20260603a1
Revises: pe20260601a1
Create Date: 2026-06-03 22:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "pf20260603a1"
down_revision: Union[str, None] = "pe20260601a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("venda_pagamentos", sa.Column("gateway_provider", sa.String(length=50), nullable=True))
    op.add_column("venda_pagamentos", sa.Column("gateway_payment_id", sa.String(length=100), nullable=True))
    op.add_column("venda_pagamentos", sa.Column("gateway_fee_amount", sa.Numeric(10, 2), nullable=True))
    op.add_column("venda_pagamentos", sa.Column("gateway_net_amount", sa.Numeric(10, 2), nullable=True))
    op.add_column("venda_pagamentos", sa.Column("gateway_gross_amount", sa.Numeric(10, 2), nullable=True))
    op.create_index("ix_venda_pagamentos_gateway_provider", "venda_pagamentos", ["gateway_provider"], unique=False)
    op.create_index("ix_venda_pagamentos_gateway_payment_id", "venda_pagamentos", ["gateway_payment_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_venda_pagamentos_gateway_payment_id", table_name="venda_pagamentos")
    op.drop_index("ix_venda_pagamentos_gateway_provider", table_name="venda_pagamentos")
    op.drop_column("venda_pagamentos", "gateway_gross_amount")
    op.drop_column("venda_pagamentos", "gateway_net_amount")
    op.drop_column("venda_pagamentos", "gateway_fee_amount")
    op.drop_column("venda_pagamentos", "gateway_payment_id")
    op.drop_column("venda_pagamentos", "gateway_provider")
