"""normalize DRE enum labels across environments

Revision ID: mo20260503a1
Revises: mn20260503a1
Create Date: 2026-05-03 00:30:00.000000
"""

from alembic import op


revision = "mo20260503a1"
down_revision = "mn20260503a1"
branch_labels = None
depends_on = None


ENUM_RENAMES = (
    ("tipocusto", "direto", "DIRETO"),
    ("tipocusto", "indireto_rateavel", "INDIRETO_RATEAVEL"),
    ("tipocusto", "corporativo", "CORPORATIVO"),
    ("baserateio", "faturamento", "FATURAMENTO"),
    ("baserateio", "pedidos", "PEDIDOS"),
    ("baserateio", "percentual", "PERCENTUAL"),
    ("baserateio", "manual", "MANUAL"),
    ("escoporateio", "loja_fisica", "LOJA_FISICA"),
    ("escoporateio", "online", "ONLINE"),
    ("escoporateio", "ambos", "AMBOS"),
    ("escopo_rateio", "loja_fisica", "LOJA_FISICA"),
    ("escopo_rateio", "online", "ONLINE"),
    ("escopo_rateio", "ambos", "AMBOS"),
)


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _rename_enum_label(enum_type: str, old_label: str, new_label: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                  FROM pg_type t
                  JOIN pg_enum e ON e.enumtypid = t.oid
                 WHERE t.typname = {_literal(enum_type)}
                   AND e.enumlabel = {_literal(old_label)}
            )
            AND NOT EXISTS (
                SELECT 1
                  FROM pg_type t
                  JOIN pg_enum e ON e.enumtypid = t.oid
                 WHERE t.typname = {_literal(enum_type)}
                   AND e.enumlabel = {_literal(new_label)}
            )
            THEN
                ALTER TYPE {enum_type} RENAME VALUE {_literal(old_label)} TO {_literal(new_label)};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    for enum_type, old_label, new_label in ENUM_RENAMES:
        _rename_enum_label(enum_type, old_label, new_label)


def downgrade() -> None:
    # Keep the canonical enum labels aligned with SQLAlchemy's enum names.
    pass
