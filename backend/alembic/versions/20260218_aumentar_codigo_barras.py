"""aumentar_codigo_barras_varchar20

Revision ID: 20260218_aumentar_codigo_barras
Revises: 20260216_add_rateio_to_notas_entrada
Create Date: 2026-02-18 03:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260218_aumentar_codigo_barras'
down_revision = '20260216_add_rateio_to_notas_entrada'
branch_labels = None
depends_on = None


def upgrade():
    """
    Aumenta o tamanho da coluna codigo_barras de VARCHAR(13) para VARCHAR(20)
    para suportar códigos de barras EAN-14 e outros formatos maiores.
    """
    # Alterar coluna codigo_barras
    op.alter_column(
        'produtos',
        'codigo_barras',
        type_=sa.String(20),
        existing_type=sa.String(13),
        existing_nullable=True
    )


def downgrade():
    """
    Reverte a alteração, diminuindo codigo_barras de VARCHAR(20) para VARCHAR(13).
    ATENÇÃO: Se houver códigos com mais de 13 caracteres, eles serão truncados.
    """
    # Reverter alteração da coluna codigo_barras
    op.alter_column(
        'produtos',
        'codigo_barras',
        type_=sa.String(13),
        existing_type=sa.String(20),
        existing_nullable=True
    )
