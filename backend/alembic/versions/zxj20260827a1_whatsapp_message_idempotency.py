"""prevent duplicate WhatsApp provider messages

Revision ID: zxj20260827a1
Revises: zxi20260827a1
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


revision = "zxj20260827a1"
down_revision = "zxi20260827a1"
branch_labels = None
depends_on = None


TABLE_NAME = "whatsapp_ia_messages"
INDEX_NAME = "ux_whatsapp_ia_messages_tenant_provider_message"


def _table_supports_idempotency(bind) -> bool:
    inspector = sa.inspect(bind)
    if not inspector.has_table(TABLE_NAME):
        return False
    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    return {"id", "tenant_id", "whatsapp_message_id"}.issubset(columns)


def _index_exists(bind) -> bool:
    inspector = sa.inspect(bind)
    return any(
        index.get("name") == INDEX_NAME for index in inspector.get_indexes(TABLE_NAME)
    )


def _clear_repeated_historical_ids(bind) -> None:
    duplicate_groups = bind.execute(
        sa.text(f"""
            SELECT tenant_id, whatsapp_message_id, MIN(id) AS kept_id
            FROM {TABLE_NAME}
            WHERE whatsapp_message_id IS NOT NULL
              AND trim(CAST(whatsapp_message_id AS TEXT)) <> ''
            GROUP BY tenant_id, whatsapp_message_id
            HAVING COUNT(*) > 1
            """)
    ).mappings()

    for group in duplicate_groups:
        bind.execute(
            sa.text(f"""
                UPDATE {TABLE_NAME}
                SET whatsapp_message_id = NULL
                WHERE tenant_id = :tenant_id
                  AND whatsapp_message_id = :whatsapp_message_id
                  AND id <> :kept_id
                """),
            {
                "tenant_id": group["tenant_id"],
                "whatsapp_message_id": group["whatsapp_message_id"],
                "kept_id": group["kept_id"],
            },
        )


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_supports_idempotency(bind):
        return

    _clear_repeated_historical_ids(bind)
    if _index_exists(bind):
        return

    op.create_index(
        INDEX_NAME,
        TABLE_NAME,
        ["tenant_id", "whatsapp_message_id"],
        unique=True,
        postgresql_where=sa.text(
            "whatsapp_message_id IS NOT NULL AND btrim(whatsapp_message_id) <> ''"
        ),
        sqlite_where=sa.text(
            "whatsapp_message_id IS NOT NULL AND trim(whatsapp_message_id) <> ''"
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _table_supports_idempotency(bind) or not _index_exists(bind):
        return
    op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
