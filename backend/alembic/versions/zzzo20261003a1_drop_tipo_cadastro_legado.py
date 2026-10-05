"""remove tipo_cadastro legado: clientes e pessoa_mestre passam a usar so as flags

Revision ID: zzzo20261003a1
Revises: zzzn20261003a1
Create Date: 2026-10-03

Antes de dropar a coluna, reaplica o backfill tipo_cadastro -> flag (so acrescenta
true, idempotente) para garantir que nenhum tipo se perca em bases que ainda
tenham linhas divergentes. Depois remove a coluna legada de clientes e de
pessoa_mestre, trocando-a pelas 4 flags booleanas na tabela pessoa_mestre.

Downgrade reconstroi tipo_cadastro a partir das flags (ordem fixa: cliente,
fornecedor, veterinario, funcionario) — perde a informacao de multiplos tipos
no campo legado, que nao existia antes da migracao das flags.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "zzzo20261003a1"
down_revision: Union[str, None] = "zzzn20261003a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for tipo in ("cliente", "fornecedor", "veterinario", "funcionario"):
        op.execute(
            f"UPDATE clientes SET is_{tipo} = true "
            f"WHERE tipo_cadastro = '{tipo}' AND is_{tipo} IS NOT TRUE"
        )
    op.execute(
        """
        UPDATE clientes SET is_cliente = true
        WHERE NOT (is_cliente OR is_fornecedor OR is_veterinario OR is_funcionario)
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_clientes_tipo_cadastro")
    op.drop_column("clientes", "tipo_cadastro")

    for campo in ("is_cliente", "is_fornecedor", "is_veterinario", "is_funcionario"):
        op.add_column(
            "pessoa_mestre",
            sa.Column(campo, sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    for tipo in ("cliente", "fornecedor", "veterinario", "funcionario"):
        op.execute(
            f"UPDATE pessoa_mestre SET is_{tipo} = true "
            f"WHERE tipo_cadastro LIKE '%{tipo}%'"
        )
    op.drop_column("pessoa_mestre", "tipo_cadastro")


def downgrade() -> None:
    op.add_column(
        "pessoa_mestre", sa.Column("tipo_cadastro", sa.String(length=50), nullable=True)
    )
    op.execute(
        """
        UPDATE pessoa_mestre SET tipo_cadastro = array_to_string(ARRAY_REMOVE(ARRAY[
            CASE WHEN is_cliente THEN 'cliente' END,
            CASE WHEN is_fornecedor THEN 'fornecedor' END,
            CASE WHEN is_veterinario THEN 'veterinario' END,
            CASE WHEN is_funcionario THEN 'funcionario' END
        ], NULL), ' / ')
        """
    )
    for campo in ("is_cliente", "is_fornecedor", "is_veterinario", "is_funcionario"):
        op.drop_column("pessoa_mestre", campo)

    op.add_column(
        "clientes",
        sa.Column(
            "tipo_cadastro",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'cliente'"),
        ),
    )
    op.execute(
        """
        UPDATE clientes SET tipo_cadastro = CASE
            WHEN is_cliente THEN 'cliente'
            WHEN is_fornecedor THEN 'fornecedor'
            WHEN is_veterinario THEN 'veterinario'
            WHEN is_funcionario THEN 'funcionario'
            ELSE 'cliente'
        END
        """
    )
    op.create_index("ix_clientes_tipo_cadastro", "clientes", ["tipo_cadastro"])
