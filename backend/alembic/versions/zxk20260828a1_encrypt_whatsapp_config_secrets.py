"""encrypt WhatsApp tenant configuration secrets

Revision ID: zxk20260828a1
Revises: zxj20260827a1
Create Date: 2026-08-28
"""

from alembic import op
import sqlalchemy as sa

from app.security.tenant_config_crypto import (
    decrypt_secret_strict,
    encrypt_secret,
)


revision = "zxk20260828a1"
down_revision = "zxj20260827a1"
branch_labels = None
depends_on = None


TABLE_NAME = "tenant_whatsapp_config"
SECRET_COLUMNS = {
    "api_key": "api_key_encrypted",
    "webhook_secret": "webhook_secret_encrypted",
    "openai_api_key": "openai_api_key_encrypted",
}


def _column_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    if not inspector.has_table(TABLE_NAME):
        return set()
    return {column["name"] for column in inspector.get_columns(TABLE_NAME)}


def _set_rls_enabled(bind, *, enabled: bool) -> None:
    if bind.dialect.name != "postgresql":
        return
    if enabled:
        op.execute(sa.text(f"ALTER TABLE {TABLE_NAME} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {TABLE_NAME} FORCE ROW LEVEL SECURITY"))
    else:
        op.execute(sa.text(f"ALTER TABLE {TABLE_NAME} NO FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {TABLE_NAME} DISABLE ROW LEVEL SECURITY"))


def _secret_rows(bind):
    selected_columns = ", ".join(["id", *SECRET_COLUMNS, *SECRET_COLUMNS.values()])
    return bind.execute(
        sa.text(f"SELECT {selected_columns} FROM {TABLE_NAME}")
    ).mappings()


def upgrade() -> None:
    bind = op.get_bind()
    columns = _column_names(bind)
    if not columns or not set(SECRET_COLUMNS).issubset(columns):
        return

    for encrypted_column in SECRET_COLUMNS.values():
        if encrypted_column not in columns:
            op.add_column(TABLE_NAME, sa.Column(encrypted_column, sa.Text()))

    _set_rls_enabled(bind, enabled=False)
    try:
        for row in _secret_rows(bind):
            encrypted_values = {
                encrypted_column: encrypt_secret(
                    row.get(encrypted_column) or row.get(legacy_column)
                )
                for legacy_column, encrypted_column in SECRET_COLUMNS.items()
            }
            bind.execute(
                sa.text(f"""
                    UPDATE {TABLE_NAME}
                    SET api_key = NULL,
                        webhook_secret = NULL,
                        openai_api_key = NULL,
                        api_key_encrypted = :api_key_encrypted,
                        webhook_secret_encrypted = :webhook_secret_encrypted,
                        openai_api_key_encrypted = :openai_api_key_encrypted
                    WHERE id = :config_id
                    """),
                {"config_id": row["id"], **encrypted_values},
            )
    finally:
        _set_rls_enabled(bind, enabled=True)


def downgrade() -> None:
    bind = op.get_bind()
    columns = _column_names(bind)
    encrypted_columns = set(SECRET_COLUMNS.values())
    if not columns or not encrypted_columns.issubset(columns):
        return

    _set_rls_enabled(bind, enabled=False)
    try:
        for row in _secret_rows(bind):
            plaintext_values = {
                legacy_column: decrypt_secret_strict(row.get(encrypted_column)) or None
                for legacy_column, encrypted_column in SECRET_COLUMNS.items()
            }
            bind.execute(
                sa.text(f"""
                    UPDATE {TABLE_NAME}
                    SET api_key = :api_key,
                        webhook_secret = :webhook_secret,
                        openai_api_key = :openai_api_key
                    WHERE id = :config_id
                    """),
                {"config_id": row["id"], **plaintext_values},
            )
    finally:
        _set_rls_enabled(bind, enabled=True)

    for encrypted_column in reversed(tuple(SECRET_COLUMNS.values())):
        op.drop_column(TABLE_NAME, encrypted_column)
