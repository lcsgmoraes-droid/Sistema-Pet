"""kit_config_fiscal_v2

Revision ID: 0c82ba32236c
Revises: 2dd161dd645b
Create Date: 2026-01-30 23:50:13.430169

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c82ba32236c'
down_revision: Union[str, Sequence[str], None] = '2dd161dd645b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Criar tabela kit_config_fiscal."""
    
    op.create_table(
        "kit_config_fiscal",
        sa.Column("id", sa.Integer, primary_key=True),

        # Multi-tenant
        sa.Column("tenant_id", sa.Integer, nullable=False, index=True),

        # KIT (produto com tipo_produto = 'KIT')
        sa.Column(
            "produto_kit_id",
            sa.Integer,
            sa.ForeignKey("produtos.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),

        # Controle de herança
        sa.Column(
            "herdado_da_empresa",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),

        # === Identificação fiscal ===
        sa.Column("origem_mercadoria", sa.String(1)),
        sa.Column("ncm", sa.String(10)),
        sa.Column("cest", sa.String(10)),
        sa.Column("cfop", sa.String(4)),

        # === ICMS ===
        sa.Column("cst_icms", sa.String(3)),
        sa.Column("icms_aliquota", sa.Numeric(5, 2)),
        sa.Column("icms_st", sa.Boolean),

        # === PIS / COFINS ===
        sa.Column("pis_aliquota", sa.Numeric(5, 2)),
        sa.Column("cofins_aliquota", sa.Numeric(5, 2)),

        # Auditoria
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Remover tabela kit_config_fiscal."""
    
    op.drop_table("kit_config_fiscal")
