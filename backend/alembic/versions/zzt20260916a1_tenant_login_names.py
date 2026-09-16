"""Separa o nome de acesso do nome fantasia da empresa.

Revision ID: zzt20260916a1
Revises: zzt20260915a1
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "zzt20260916a1"
down_revision = "zzt20260915a1"
branch_labels = None
depends_on = None


def _tenant_id_type(inspector: sa.Inspector) -> sa.types.TypeEngine:
    """Replica o tipo real de tenants.id (UUID ou VARCHAR historico)."""
    for column in inspector.get_columns("tenants"):
        if column["name"] == "id":
            return column["type"].copy()
    raise RuntimeError("Coluna tenants.id nao encontrada")


def upgrade() -> None:
    tenant_id_type = _tenant_id_type(sa.inspect(op.get_bind()))

    op.drop_index("ux_tenants_name_normalized", table_name="tenants")
    op.create_index(
        "ix_tenants_name_normalized",
        "tenants",
        ["name_normalized"],
        unique=False,
    )

    op.create_table(
        "tenant_login_names",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", tenant_id_type, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_normalized", sa.String(length=255), nullable=False),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tenant_login_names_tenant_id",
        "tenant_login_names",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ux_tenant_login_names_name_normalized",
        "tenant_login_names",
        ["name_normalized"],
        unique=True,
    )
    op.create_index(
        "ux_tenant_login_names_primary_tenant",
        "tenant_login_names",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true"),
        sqlite_where=sa.text("is_primary = 1"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO tenant_login_names (
                tenant_id, name, name_normalized, is_primary, created_at, updated_at
            )
            SELECT id, name, name_normalized, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM tenants
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    duplicate = connection.execute(
        sa.text(
            """
            SELECT name_normalized
            FROM tenants
            GROUP BY name_normalized
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate:
        raise RuntimeError(
            "Nao e possivel reverter: existem nomes fantasia duplicados entre tenants."
        )

    op.drop_table("tenant_login_names")
    op.drop_index("ix_tenants_name_normalized", table_name="tenants")
    op.create_index(
        "ux_tenants_name_normalized",
        "tenants",
        ["name_normalized"],
        unique=True,
    )
