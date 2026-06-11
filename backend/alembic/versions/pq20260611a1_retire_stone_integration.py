"""retire stone online integration and scrub stored secrets

Revision ID: pq20260611a1
Revises: pp20260611a1
Create Date: 2026-06-11

The online Stone/Pagar.me integration is discontinued. Keep historical tables
for audit/reference, but disable active configs and remove plaintext credentials.
"""

from alembic import op


revision = "pq20260611a1"
down_revision = "pp20260611a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE stone_configs
            ALTER COLUMN client_id DROP NOT NULL,
            ALTER COLUMN client_secret DROP NOT NULL
        """
    )
    op.execute(
        """
        UPDATE stone_configs
        SET
            active = FALSE,
            webhook_enabled = FALSE,
            enable_pix = FALSE,
            enable_credit_card = FALSE,
            enable_debit_card = FALSE,
            client_id = '',
            client_secret = '',
            merchant_id = NULL,
            webhook_secret = NULL,
            conciliacao_client_id = NULL,
            conciliacao_client_secret = NULL,
            affiliation_code = NULL,
            documento = NULL,
            conciliacao_username = NULL,
            conciliacao_password_enc = NULL,
            pos_serial_number = NULL,
            updated_at = NOW()
        """
    )


def downgrade() -> None:
    # Security migration: plaintext credentials cannot and should not be restored.
    pass
