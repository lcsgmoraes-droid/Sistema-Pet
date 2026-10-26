"""Distingue evidencias de simulador local e API real no estoque iFood.

Revision ID: zzzzw20261025a1
Revises: zzzzv20261024a1
"""

from alembic import op
import sqlalchemy as sa

revision = "zzzzw20261025a1"
down_revision = "zzzzv20261024a1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL row_security = off")
    op.add_column(
        "ifood_catalog_submissions",
        sa.Column(
            "provider_mode", sa.String(16), nullable=False, server_default="ifood_api"
        ),
    )
    # Todos os auto_stock anteriores pertencem ao piloto que bloqueava a rede
    # externa. Uma atualizacao nao pode transforma-los em prova da API real.
    op.execute(
        "UPDATE ifood_catalog_submissions SET provider_mode = 'local_simulator' "
        "WHERE source = 'auto_stock'"
    )
    op.create_check_constraint(
        "ck_ifood_catalog_submission_provider_mode",
        "ifood_catalog_submissions",
        "provider_mode IN ('local_simulator','ifood_api')",
    )
    op.add_column(
        "ifood_stock_sync_states",
        sa.Column(
            "provider_mode",
            sa.String(16),
            nullable=False,
            server_default="local_simulator",
        ),
    )
    op.create_check_constraint(
        "ck_ifood_stock_sync_provider_mode",
        "ifood_stock_sync_states",
        "provider_mode IN ('local_simulator','ifood_api')",
    )


def downgrade():
    # Remover a origem depois de uma tentativa real poderia apresentar sua
    # evidencia como simulacao. Preserve a trilha e falhe fechado sob RLS.
    op.execute("SET LOCAL row_security = off")
    bind = op.get_bind()
    found = bind.execute(
        sa.text(
            "SELECT 1 FROM ifood_catalog_submissions "
            "WHERE source = 'auto_stock' AND provider_mode = 'ifood_api' LIMIT 1"
        )
    ).first()
    live_state = bind.execute(
        sa.text(
            "SELECT 1 FROM ifood_stock_sync_states "
            "WHERE provider_mode = 'ifood_api' LIMIT 1"
        )
    ).first()
    if found or live_state:
        raise RuntimeError(
            "Existe historico real de estoque iFood; downgrade recusado."
        )
    op.drop_constraint(
        "ck_ifood_stock_sync_provider_mode", "ifood_stock_sync_states", type_="check"
    )
    op.drop_column("ifood_stock_sync_states", "provider_mode")
    op.drop_constraint(
        "ck_ifood_catalog_submission_provider_mode",
        "ifood_catalog_submissions",
        type_="check",
    )
    op.drop_column("ifood_catalog_submissions", "provider_mode")
