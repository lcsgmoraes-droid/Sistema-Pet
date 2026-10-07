"""merge heads: contatos/vendedor/cashback (main) + origem/historico/registros clinicos/RLS (documentacao)

Revision ID: zzzw20261006a1
Revises: zzzj20261006a1, zzzv20261005a1
Create Date: 2026-10-06

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "zzzw20261006a1"
down_revision: Union[str, Sequence[str], None] = ("zzzj20261006a1", "zzzv20261005a1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migracao apenas de merge de heads; nenhuma alteracao de schema.
    pass


def downgrade() -> None:
    # Migracao apenas de merge de heads; nenhuma alteracao de schema.
    pass
