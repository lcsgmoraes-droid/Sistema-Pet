"""normalize NaturezaDRE labels to the values used by the ORM

Revision ID: zxc20260826a1
Revises: zxb20260826a1
Create Date: 2026-08-26

The original PostgreSQL enum was created with member names in uppercase,
while the current ORM explicitly persists the lowercase enum values. This
migration makes new and existing databases follow the same contract.
"""

from alembic import op


revision = "zxc20260826a1"
down_revision = "zxb20260826a1"
branch_labels = None
depends_on = None

ENUM_TYPE = "naturezadre"
LABEL_RENAMES = (
    ("RECEITA", "receita"),
    ("CUSTO", "custo"),
    ("DESPESA", "despesa"),
    ("RESULTADO", "resultado"),
)


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _normalize_label(old_label: str, new_label: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                  FROM pg_type t
                  JOIN pg_enum e ON e.enumtypid = t.oid
                 WHERE t.typname = {_literal(ENUM_TYPE)}
                   AND e.enumlabel = {_literal(old_label)}
            )
            AND NOT EXISTS (
                SELECT 1
                  FROM pg_type t
                  JOIN pg_enum e ON e.enumtypid = t.oid
                 WHERE t.typname = {_literal(ENUM_TYPE)}
                   AND e.enumlabel = {_literal(new_label)}
            )
            THEN
                ALTER TYPE {ENUM_TYPE}
                    RENAME VALUE {_literal(old_label)} TO {_literal(new_label)};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    for old_label, new_label in LABEL_RENAMES:
        _normalize_label(old_label, new_label)


def downgrade() -> None:
    """Keep the database aligned with the current ORM value contract."""
