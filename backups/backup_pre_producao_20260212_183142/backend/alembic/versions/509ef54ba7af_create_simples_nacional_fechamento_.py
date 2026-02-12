"""create simples nacional fechamento mensal

Revision ID: 509ef54ba7af
Revises: 2e9c2acefb7b
Create Date: 2026-01-31 02:49:25.695259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '509ef54ba7af'
down_revision: Union[str, Sequence[str], None] = '2e9c2acefb7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "simples_nacional_mensal",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.String, nullable=False, index=True),
        
        # Competência
        sa.Column("mes", sa.Integer, nullable=False),
        sa.Column("ano", sa.Integer, nullable=False),
        
        # Faturamento
        sa.Column("faturamento_sistema", sa.Numeric(14, 2), nullable=True, comment="Apurado via NF"),
        sa.Column("faturamento_contador", sa.Numeric(14, 2), nullable=True, comment="Informado manualmente"),
        
        # Impostos
        sa.Column("imposto_estimado", sa.Numeric(14, 2), nullable=True, comment="Provisões acumuladas"),
        sa.Column("imposto_real", sa.Numeric(14, 2), nullable=True, comment="DAS pago"),
        
        # Alíquotas
        sa.Column("aliquota_efetiva", sa.Numeric(6, 4), nullable=True, comment="Real do mês"),
        sa.Column("aliquota_sugerida", sa.Numeric(6, 4), nullable=True, comment="Sugestão para próximo mês"),
        
        # Controle
        sa.Column("fechado", sa.Boolean, server_default=sa.false()),
        sa.Column("observacoes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Índice para busca rápida por competência
    op.create_index(
        "ix_simples_mensal_competencia",
        "simples_nacional_mensal",
        ["tenant_id", "ano", "mes"],
        unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_simples_mensal_competencia", table_name="simples_nacional_mensal")
    op.drop_table("simples_nacional_mensal")
