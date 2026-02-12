"""tornar campos dre obrigatorios

Revision ID: 20260129_tornar_dre_obrigatorio
Revises: eb865c9b7f94
Create Date: 2026-01-29 16:00:00.000000

Torna NOT NULL os campos dre_subcategoria_id e canal nas tabelas de lançamentos.
Dados já foram limpos previamente.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260129_tornar_dre_obrigatorio'
down_revision: Union[str, Sequence[str], None] = 'eb865c9b7f94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Torna campos DRE obrigatórios"""
    
    # CONTAS A PAGAR
    op.alter_column('contas_pagar', 'dre_subcategoria_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('contas_pagar', 'canal',
                    existing_type=sa.String(length=50),
                    nullable=False)
    
    # CONTAS A RECEBER
    op.alter_column('contas_receber', 'dre_subcategoria_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    op.alter_column('contas_receber', 'canal',
                    existing_type=sa.String(length=50),
                    nullable=False)


def downgrade() -> None:
    """Reverte campos para nullable"""
    
    # CONTAS A RECEBER
    op.alter_column('contas_receber', 'canal',
                    existing_type=sa.String(length=50),
                    nullable=True)
    
    op.alter_column('contas_receber', 'dre_subcategoria_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # CONTAS A PAGAR
    op.alter_column('contas_pagar', 'canal',
                    existing_type=sa.String(length=50),
                    nullable=True)
    
    op.alter_column('contas_pagar', 'dre_subcategoria_id',
                    existing_type=sa.Integer(),
                    nullable=True)
