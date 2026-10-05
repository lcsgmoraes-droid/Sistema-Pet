"""restricao unica (user_id, tenant_id) em user_tenants

Revision ID: zzzp20261005a1
Revises: zzzo20261003a1
Create Date: 2026-10-05

Nao apaga duplicatas: se existir algum par usuario+loja repetido, a migration
para com erro e lista os pares, para decidirmos qual vinculo manter.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "zzzp20261005a1"
down_revision: Union[str, None] = "zzzo20261003a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conexao = op.get_bind()
    duplicados = conexao.execute(
        sa.text(
            "SELECT user_id, tenant_id, COUNT(*) FROM user_tenants "
            "GROUP BY user_id, tenant_id HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if duplicados:
        pares = ", ".join(f"(user_id={u}, tenant_id={t}, linhas={n})" for u, t, n in duplicados)
        raise RuntimeError(
            "Existem vinculos duplicados em user_tenants; resolver antes de aplicar: " + pares
        )
    op.create_unique_constraint(
        "uq_user_tenants_user_tenant", "user_tenants", ["user_id", "tenant_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_user_tenants_user_tenant", "user_tenants", type_="unique")
