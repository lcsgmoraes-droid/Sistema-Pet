"""add vet return origin to agendamentos

Revision ID: ov20260517a2
Revises: ou20260517a1
Create Date: 2026-05-17 19:12:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "ov20260517a2"
down_revision = "ou20260517a1"
branch_labels = None
depends_on = None


TABLE = "vet_agendamentos"
COLUMN = "consulta_origem_id"
INDEX = "ix_vet_agendamentos_consulta_origem_id"
FK = "fk_vet_agendamentos_consulta_origem_id"


def _inspector():
    return sa.inspect(op.get_bind())


def _columns(table_name: str) -> set[str]:
    inspector = _inspector()
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    inspector = _inspector()
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _foreign_keys(table_name: str) -> set[str]:
    inspector = _inspector()
    if not inspector.has_table(table_name):
        return set()
    return {fk["name"] for fk in inspector.get_foreign_keys(table_name)}


def upgrade() -> None:
    columns = _columns(TABLE)
    if COLUMN not in columns:
        op.add_column(TABLE, sa.Column(COLUMN, sa.Integer(), nullable=True))

    if FK not in _foreign_keys(TABLE):
        op.create_foreign_key(
            FK,
            TABLE,
            "vet_consultas",
            [COLUMN],
            ["id"],
        )

    if INDEX not in _indexes(TABLE):
        op.create_index(INDEX, TABLE, [COLUMN])


def downgrade() -> None:
    if INDEX in _indexes(TABLE):
        op.drop_index(INDEX, table_name=TABLE)

    if FK in _foreign_keys(TABLE):
        op.drop_constraint(FK, TABLE, type_="foreignkey")

    if COLUMN in _columns(TABLE):
        op.drop_column(TABLE, COLUMN)
