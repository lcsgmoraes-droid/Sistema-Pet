"""Garante unicidade do codigo por tenant em clientes

Antecipadamente renumera codigos duplicados e depois cria o constraint UNIQUE.

Revision ID: p4q5r6s7t8u9
Revises: o3p4q5r6s7t8
Create Date: 2026-03-11 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p4q5r6s7t8u9"
down_revision: Union[str, Sequence[str], None] = "o3p4q5r6s7t8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Detectar e corrigir codigos duplicados dentro do mesmo tenant.
    #    Para cada grupo (tenant_id, codigo) com mais de um registro,
    #    mantemos o cliente mais antigo (menor id) com o codigo original
    #    e renumeramos os demais com codigos novos alem do maximo atual.
    resultado = conn.execute(sa.text("""
        SELECT tenant_id, codigo, array_agg(id ORDER BY id) AS ids
        FROM clientes
        WHERE codigo IS NOT NULL
        GROUP BY tenant_id, codigo
        HAVING count(*) > 1
    """))

    duplicados = resultado.fetchall()

    for row in duplicados:
        tenant_id = row[0]
        ids = row[2]  # lista de ids ordenados; o primeiro mantem o codigo original

        ids_para_renumerar = ids[1:]

        for cliente_id in ids_para_renumerar:
            # Buscar o maior codigo numerico atual deste tenant para evitar qualquer conflito
            max_result = conn.execute(sa.text("""
                SELECT MAX(CAST(codigo AS BIGINT))
                FROM clientes
                WHERE tenant_id = :tenant_id
                  AND codigo ~ '^[0-9]+$'
            """), {"tenant_id": tenant_id})

            max_codigo = max_result.scalar() or 1000
            novo_codigo = str(max_codigo + 1)

            conn.execute(sa.text("""
                UPDATE clientes SET codigo = :novo_codigo
                WHERE id = :cliente_id
            """), {"novo_codigo": novo_codigo, "cliente_id": cliente_id})

    # 2. Agora que nao ha mais duplicatas, criar o UniqueConstraint
    op.create_unique_constraint(
        "uq_clientes_tenant_codigo",
        "clientes",
        ["tenant_id", "codigo"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_clientes_tenant_codigo", "clientes", type_="uniqueconstraint")
