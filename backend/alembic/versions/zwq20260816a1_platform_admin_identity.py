"""create tenant-independent platform administrator identity

Revision ID: zwq20260816a1
Revises: zwp20260816a1
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "zwq20260816a1"
down_revision = "zwp20260816a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_admins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("reset_token", sa.String(length=255), nullable=True),
        sa.Column("reset_token_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "failed_login_attempts", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(length=50), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_platform_admins_email"),
    )
    op.create_index("ix_platform_admins_email", "platform_admins", ["email"])
    op.create_index(
        "ix_platform_admins_reset_token", "platform_admins", ["reset_token"]
    )

    op.create_table(
        "platform_admin_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform_admin_id", sa.Integer(), nullable=False),
        sa.Column("token_jti", sa.String(length=36), nullable=False),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["platform_admin_id"], ["platform_admins.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_jti", name="uq_platform_admin_sessions_jti"),
    )
    op.create_index(
        "ix_platform_admin_sessions_admin",
        "platform_admin_sessions",
        ["platform_admin_id"],
    )
    op.create_index(
        "ix_platform_admin_sessions_expires",
        "platform_admin_sessions",
        ["expires_at"],
    )
    op.create_index(
        "ix_platform_admin_sessions_jti",
        "platform_admin_sessions",
        ["token_jti"],
    )

    # O administrador legado que ja acessava o Ops ganha uma identidade global
    # independente, inicialmente com a mesma senha. Alteracoes futuras de senha
    # em um dos ambientes nao afetam o outro.
    op.execute(
        """
        INSERT INTO platform_admins (
            email, hashed_password, name, is_active, failed_login_attempts,
            last_login_at, last_login_ip, password_changed_at
        )
        SELECT
            LOWER(TRIM(email)), hashed_password, nome, is_active,
            COALESCE(failed_login_attempts, 0), last_login_at, last_login_ip,
            password_changed_at
        FROM users
        WHERE is_admin = true
          AND hashed_password IS NOT NULL
        ON CONFLICT (email) DO NOTHING
        """
    )

    op.add_column(
        "billing_offers",
        sa.Column("created_by_platform_admin_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_billing_offers_platform_admin",
        "billing_offers",
        ["created_by_platform_admin_id"],
    )
    op.create_foreign_key(
        "fk_billing_offers_platform_admin",
        "billing_offers",
        "platform_admins",
        ["created_by_platform_admin_id"],
        ["id"],
    )
    op.alter_column(
        "billing_offers",
        "created_by_user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_billing_offers_creator",
        "billing_offers",
        "(created_by_user_id IS NOT NULL AND created_by_platform_admin_id IS NULL) "
        "OR (created_by_user_id IS NULL AND "
        "created_by_platform_admin_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_billing_offers_creator", "billing_offers", type_="check")
    # Preserva ofertas criadas pelo administrador global quando ainda existe a
    # conta legada correspondente. Se nao houver correspondencia, o NOT NULL
    # abaixo bloqueia a reversao em vez de apagar a autoria silenciosamente.
    op.execute(
        """
        UPDATE billing_offers AS offer
        SET created_by_user_id = legacy_user.id
        FROM platform_admins AS platform_admin
        JOIN users AS legacy_user
          ON LOWER(TRIM(legacy_user.email)) = LOWER(TRIM(platform_admin.email))
        WHERE offer.created_by_user_id IS NULL
          AND offer.created_by_platform_admin_id = platform_admin.id
        """
    )
    op.alter_column(
        "billing_offers",
        "created_by_user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_constraint(
        "fk_billing_offers_platform_admin", "billing_offers", type_="foreignkey"
    )
    op.drop_index("ix_billing_offers_platform_admin", table_name="billing_offers")
    op.drop_column("billing_offers", "created_by_platform_admin_id")

    op.drop_index(
        "ix_platform_admin_sessions_jti", table_name="platform_admin_sessions"
    )
    op.drop_index(
        "ix_platform_admin_sessions_expires", table_name="platform_admin_sessions"
    )
    op.drop_index(
        "ix_platform_admin_sessions_admin", table_name="platform_admin_sessions"
    )
    op.drop_table("platform_admin_sessions")
    op.drop_index("ix_platform_admins_reset_token", table_name="platform_admins")
    op.drop_index("ix_platform_admins_email", table_name="platform_admins")
    op.drop_table("platform_admins")
