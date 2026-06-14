"""enable RLS on legacy product backup tables

Revision ID: tt20260614a1
Revises: ts20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision = "tt20260614a1"
down_revision = "ts20260614a1"
branch_labels = None
depends_on = None


LEGACY_PRODUCT_BACKUP_RLS_TABLES = (
    "backup_barras_cleanup_20260327",
    "backup_produto_bling_sync_cleanup_20260327",
    "backup_produto_bling_sync_excluidos_decisao_manual_20260327",
    "backup_produto_bling_sync_excluidos_pos_barra_20260327",
    "backup_produto_bling_sync_excluidos_sku_cleanup_20260327",
    "backup_produto_kit_componentes_cleanup_20260327",
    "backup_produtos_cleanup_20260327",
    "backup_produtos_excluidos_decisao_manual_20260327",
    "backup_produtos_excluidos_pos_barra_20260327",
    "backup_produtos_excluidos_sku_cleanup_20260327",
)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=LEGACY_PRODUCT_BACKUP_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=LEGACY_PRODUCT_BACKUP_RLS_TABLES,
        enable=False,
    )
