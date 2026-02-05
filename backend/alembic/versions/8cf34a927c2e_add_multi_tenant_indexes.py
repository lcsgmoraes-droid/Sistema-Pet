"""add_multi_tenant_indexes

Revision ID: 8cf34a927c2e
Revises: 6c11cea65dd5
Create Date: 2026-01-26 20:52:35.600402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cf34a927c2e'
down_revision: Union[str, Sequence[str], None] = '6c11cea65dd5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adiciona índices compostos tenant-aware para otimizar queries multi-tenant.
    
    Índices criados:
    - (tenant_id, id) - Busca por ID dentro do tenant
    - (tenant_id, created_at) - Listagens ordenadas por data dentro do tenant
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table_name in inspector.get_table_names():
        columns = {col['name'] for col in inspector.get_columns(table_name)}

        if 'tenant_id' not in columns or 'id' not in columns:
            continue

        # Índice composto: tenant_id + id
        try:
            op.create_index(
                f'ix_{table_name}_tenant_id_id',
                table_name,
                ['tenant_id', 'id'],
                unique=False
            )
            print(f"✅ Índice criado: ix_{table_name}_tenant_id_id")
        except Exception as e:
            print(f"⚠️ Índice já existe ou erro: ix_{table_name}_tenant_id_id - {e}")

        # Índice composto: tenant_id + created_at (se existir)
        if 'created_at' in columns:
            try:
                op.create_index(
                    f'ix_{table_name}_tenant_id_created_at',
                    table_name,
                    ['tenant_id', 'created_at'],
                    unique=False
                )
                print(f"✅ Índice criado: ix_{table_name}_tenant_id_created_at")
            except Exception as e:
                print(f"⚠️ Índice já existe ou erro: ix_{table_name}_tenant_id_created_at - {e}")


def downgrade() -> None:
    """Remove índices compostos multi-tenant."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table_name in inspector.get_table_names():
        for index in inspector.get_indexes(table_name):
            if index['name'].startswith('ix_') and 'tenant_id' in index['name']:
                try:
                    op.drop_index(index['name'], table_name=table_name)
                    print(f"✅ Índice removido: {index['name']}")
                except Exception as e:
                    print(f"⚠️ Erro ao remover índice: {index['name']} - {e}")

