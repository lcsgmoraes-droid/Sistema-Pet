"""create missing card conciliation tables

Revision ID: zwn20260813a1
Revises: zwm20260813a1
Create Date: 2026-08-13

The conciliation ORM models have been in active use, but the baseline database
does not contain their tables.  This repair migration creates exactly the
tables described by the current models, in dependency order, and then protects
them with the same tenant RLS policy used by the rest of the application.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.db import Base
from app.tenant_rls_migration import apply_tenant_rls

# Importing registers the exact table metadata used by the running routes.
from app import conciliacao_models as _conciliation_models  # noqa: F401, E402
from app import conciliacao_recebimento_models as _receiving_models  # noqa: F401, E402


revision = "zwn20260813a1"
down_revision = "zwm20260813a1"
branch_labels = None
depends_on = None


TABLE_NAMES = (
    "empresa_parametros",
    "adquirentes_templates",
    "arquivos_evidencia",
    "conciliacao_importacoes",
    "conciliacao_lotes",
    "conciliacao_validacoes",
    "conciliacao_logs",
    "conciliacao_recebimentos",
    "conciliacao_metricas",
    "historico_conciliacao",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in TABLE_NAMES:
        if not inspector.has_table(table_name):
            Base.metadata.tables[table_name].create(bind=bind, checkfirst=True)
            inspector = sa.inspect(bind)

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=TABLE_NAMES,
        enable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=TABLE_NAMES,
        enable=False,
    )

    for table_name in reversed(TABLE_NAMES):
        if inspector.has_table(table_name):
            Base.metadata.tables[table_name].drop(bind=bind, checkfirst=True)
            inspector = sa.inspect(bind)
