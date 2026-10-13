"""merge heads: main (caixa/PDV/estoque/comissoes, ate 774130f27) + documentacao (pessoa/pet por grupo comercial, zzzy20261009a1)

Revision ID: zzzz20261013a1
Revises: zzzn20261009a1, zzzy20261009a1
Create Date: 2026-10-13

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "zzzz20261013a1"
down_revision: Union[str, Sequence[str], None] = ("zzzn20261009a1", "zzzy20261009a1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migracao apenas de merge de heads; nenhuma alteracao de schema.
    pass


def downgrade() -> None:
    pass
