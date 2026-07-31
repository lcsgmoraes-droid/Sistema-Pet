"""separa conta da pessoa e audita fusoes

Revision ID: zwp20260731a1
Revises: zwo20260729a1
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zwp20260731a1"
down_revision = "zwo20260729a1"
branch_labels = None
depends_on = None

MERGE_LOG_TABLE = "pessoa_merge_logs"
MERGE_LOG_POLICY = "pessoa_merge_logs_tenant_isolation"
TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.add_column("clientes", sa.Column("auth_user_id", sa.Integer(), nullable=True))
    op.add_column("clientes", sa.Column("merged_into_id", sa.Integer(), nullable=True))
    op.create_index("ix_clientes_auth_user_id", "clientes", ["auth_user_id"])
    op.create_index("ix_clientes_merged_into_id", "clientes", ["merged_into_id"])
    op.create_foreign_key(
        "fk_clientes_auth_user_id_users",
        "clientes",
        "users",
        ["auth_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_clientes_merged_into_id_clientes",
        "clientes",
        "clientes",
        ["merged_into_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Migra apenas vinculos em que a identidade da pessoa combina com a conta.
    # Isso evita transformar o antigo "usuario que cadastrou" em dono de todas
    # as pessoas que ele criou.
    op.execute(
        """
        UPDATE clientes c
           SET auth_user_id = u.id
          FROM users u
         WHERE c.user_id = u.id
           AND c.tenant_id = u.tenant_id
           AND (
                (c.email IS NOT NULL AND lower(trim(c.email)) = lower(trim(u.email)))
             OR (
                  c.cpf IS NOT NULL AND u.cpf_cnpj IS NOT NULL
                  AND regexp_replace(c.cpf, '\\D', '', 'g') <> ''
                  AND regexp_replace(c.cpf, '\\D', '', 'g') =
                      regexp_replace(u.cpf_cnpj, '\\D', '', 'g')
                )
             OR (
                  u.telefone IS NOT NULL
                  AND regexp_replace(u.telefone, '\\D', '', 'g') <> ''
                  AND regexp_replace(u.telefone, '\\D', '', 'g') IN (
                      regexp_replace(coalesce(c.telefone, ''), '\\D', '', 'g'),
                      regexp_replace(coalesce(c.celular, ''), '\\D', '', 'g')
                  )
                )
           )
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY tenant_id, auth_user_id
                       ORDER BY CASE WHEN ativo IS TRUE THEN 0 ELSE 1 END, id
                   ) AS posicao
              FROM clientes
             WHERE auth_user_id IS NOT NULL
               AND (ativo IS TRUE OR ativo IS NULL)
        )
        UPDATE clientes c
           SET auth_user_id = NULL
          FROM ranked r
         WHERE c.id = r.id
           AND r.posicao > 1
        """
    )
    op.create_index(
        "uq_clientes_tenant_auth_user_ativo",
        "clientes",
        ["tenant_id", "auth_user_id"],
        unique=True,
        postgresql_where=sa.text(
            "auth_user_id IS NOT NULL AND (ativo IS TRUE OR ativo IS NULL)"
        ),
    )
    op.execute(
        """
        UPDATE app_access_profiles a
           SET user_id = c.auth_user_id
          FROM clientes c
         WHERE a.cliente_id = c.id
           AND a.tenant_id = c.tenant_id
           AND c.auth_user_id IS NOT NULL
        """
    )

    op.create_table(
        "pessoa_merge_logs",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_id", sa.Integer(), nullable=False),
        sa.Column("duplicado_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("modo", sa.String(length=30), nullable=False, server_default="manual"),
        sa.Column("motivo", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="concluida",
        ),
        sa.Column("snapshot_antes", sa.JSON(), nullable=False),
        sa.Column("resumo_transferencias", sa.JSON(), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["principal_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["duplicado_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_pessoa_merge_logs_tenant_id", "pessoa_merge_logs", ["tenant_id"]
    )
    op.create_index(
        "ix_pessoa_merge_logs_principal_id", "pessoa_merge_logs", ["principal_id"]
    )
    op.create_index(
        "ix_pessoa_merge_logs_duplicado_id", "pessoa_merge_logs", ["duplicado_id"]
    )
    op.create_index(
        "ix_pessoa_merge_logs_actor_user_id", "pessoa_merge_logs", ["actor_user_id"]
    )
    op.create_index(
        "ix_pessoa_merge_logs_tenant_principal",
        "pessoa_merge_logs",
        ["tenant_id", "principal_id"],
    )
    op.create_index(
        "ix_pessoa_merge_logs_tenant_duplicado",
        "pessoa_merge_logs",
        ["tenant_id", "duplicado_id"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"ALTER TABLE {MERGE_LOG_TABLE} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {MERGE_LOG_TABLE} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {MERGE_LOG_POLICY} ON {MERGE_LOG_TABLE} "
            f"USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            f"DROP POLICY IF EXISTS {MERGE_LOG_POLICY} ON {MERGE_LOG_TABLE}"
        )
    op.drop_table("pessoa_merge_logs")
    op.drop_constraint("fk_clientes_merged_into_id_clientes", "clientes", type_="foreignkey")
    op.drop_constraint("fk_clientes_auth_user_id_users", "clientes", type_="foreignkey")
    op.drop_index("uq_clientes_tenant_auth_user_ativo", table_name="clientes")
    op.drop_index("ix_clientes_merged_into_id", table_name="clientes")
    op.drop_index("ix_clientes_auth_user_id", table_name="clientes")
    op.drop_column("clientes", "merged_into_id")
    op.drop_column("clientes", "auth_user_id")
