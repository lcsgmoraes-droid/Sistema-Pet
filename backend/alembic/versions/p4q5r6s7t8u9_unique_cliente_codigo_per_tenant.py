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
    #    e renumeramos os demais com o proximo codigo disponivel do mesmo prefixo.
    #
    #    Logica de prefixo:
    #      codigo comeca com '1' -> proximo livre em 1001+
    #      codigo comeca com '2' -> proximo livre em 2001+
    #      codigo comeca com '3' -> proximo livre em 3001+
    #      ... e assim por diante
    #
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
        codigo_duplicado = row[1]
        ids = row[2]  # lista de ids, o primeiro e o "dono" original

        # Prefixo do codigo (primeiro digito)
        prefixo = codigo_duplicado[0] if codigo_duplicado else "9"

        # Os IDs que precisam ser renumerados (todos exceto o primeiro/mais antigo)
        ids_para_renumerar = ids[1:]

        for cliente_id in ids_para_renumerar:
            # Buscar todos os codigos ja usados por esse prefixo neste tenant
            codigos_usados_result = conn.execute(sa.text("""
                SELECT codigo FROM clientes
                WHERE tenant_id = :tenant_id
                  AND codigo LIKE :like_prefixo
                  AND codigo ~ '^[0-9]+$'
            """), {"tenant_id": tenant_id, "like_prefixo": prefixo + "%"})

            codigos_usados = {int(r[0]) for r in codigos_usados_result if r[0] and r[0].isdigit()}

            # Encontrar proximo disponivel
            base = int(prefixo) * 1000 + 1
            proximo = base
            while proximo in codigos_usados:
                proximo += 1

            conn.execute(sa.text("""
                UPDATE clientes SET codigo = :novo_codigo
                WHERE id = :cliente_id
            """), {"novo_codigo": str(proximo), "cliente_id": cliente_id})

    # 2. Agora que nao ha mais duplicatas, criar o UniqueConstraint
    op.create_unique_constraint(
        "uq_clientes_tenant_codigo",
        "clientes",
        ["tenant_id", "codigo"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_clientes_tenant_codigo", "clientes", type_="uniqueconstraint")
