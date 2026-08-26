"""repair missing tenant ecommerce slug

Revision ID: zxb20260826a1
Revises: zxa20260824a1
Create Date: 2026-08-26

The ORM and storefront routes use ``tenants.ecommerce_slug``, but the column
was never added to the Alembic chain. Existing installations may already have
it from an older manual schema sync, so this repair must be idempotent.
"""

from alembic import op
import sqlalchemy as sa


revision = "zxb20260826a1"
down_revision = "zxa20260824a1"
branch_labels = None
depends_on = None

TABLE_NAME = "tenants"
COLUMN_NAME = "ecommerce_slug"
INDEX_NAME = "ix_tenants_ecommerce_slug"


def _has_unique_slug(inspector: sa.Inspector) -> bool:
    unique_indexes = (
        index
        for index in inspector.get_indexes(TABLE_NAME)
        if index.get("unique") is True
    )
    unique_constraints = inspector.get_unique_constraints(TABLE_NAME)
    return any(
        item.get("column_names") == [COLUMN_NAME]
        for item in (*unique_indexes, *unique_constraints)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if COLUMN_NAME not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column(COLUMN_NAME, sa.String(length=80), nullable=True),
        )
        inspector = sa.inspect(bind)

    if _has_unique_slug(inspector):
        return

    indexes = {index["name"]: index for index in inspector.get_indexes(TABLE_NAME)}
    if INDEX_NAME in indexes:
        raise RuntimeError(
            f"O indice {INDEX_NAME} existe, mas nao protege a unicidade do slug."
        )

    duplicate_slug = bind.execute(
        sa.text(
            """
            SELECT ecommerce_slug
              FROM tenants
             WHERE ecommerce_slug IS NOT NULL
             GROUP BY ecommerce_slug
            HAVING COUNT(*) > 1
             LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if duplicate_slug is not None:
        raise RuntimeError(
            "Existem empresas com ecommerce_slug duplicado; corrija antes da migracao."
        )

    op.create_index(
        INDEX_NAME,
        TABLE_NAME,
        [COLUMN_NAME],
        unique=True,
    )


def downgrade() -> None:
    """Forward-only repair: do not remove a column that may predate Alembic."""
