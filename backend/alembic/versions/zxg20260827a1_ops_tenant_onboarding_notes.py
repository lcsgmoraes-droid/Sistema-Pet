"""add next contact and immutable onboarding notes

Revision ID: zxg20260827a1
Revises: zxf20260827a1
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa

revision = "zxg20260827a1"
down_revision = "zxf20260827a1"
branch_labels = None
depends_on = None


def _tenant_id_type(inspector: sa.Inspector) -> sa.types.TypeEngine:
    """Replica o tipo real de tenants.id em bancos historicos e atuais."""

    for column in inspector.get_columns("tenants"):
        if column["name"] == "id":
            return column["type"].copy()
    raise RuntimeError("Coluna tenants.id nao encontrada")


def upgrade() -> None:
    tenant_id_type = _tenant_id_type(sa.inspect(op.get_bind()))
    op.add_column(
        "tenants",
        sa.Column("onboarding_next_contact_on", sa.Date(), nullable=True),
    )
    op.create_table(
        "ops_tenant_onboarding_notes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", tenant_id_type, nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("next_contact_on", sa.Date(), nullable=True),
        sa.Column("created_by_platform_admin_id", sa.Integer(), nullable=False),
        sa.Column("created_by_label", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(note) BETWEEN 3 AND 1000",
            name="ck_ops_tenant_onboarding_notes_length",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_platform_admin_id"],
            ["platform_admins.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ops_tenant_onboarding_notes_created_at",
        "ops_tenant_onboarding_notes",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ops_tenant_onboarding_notes_created_by_platform_admin_id",
        "ops_tenant_onboarding_notes",
        ["created_by_platform_admin_id"],
        unique=False,
    )
    op.create_index(
        "ix_ops_tenant_onboarding_notes_tenant_id",
        "ops_tenant_onboarding_notes",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_ops_tenant_onboarding_notes_tenant_created",
        "ops_tenant_onboarding_notes",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("ops_tenant_onboarding_notes")
    op.drop_column("tenants", "onboarding_next_contact_on")
