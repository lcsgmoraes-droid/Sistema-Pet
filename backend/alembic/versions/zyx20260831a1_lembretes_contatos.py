"""add contact history for recurrence reminders

Revision ID: zyx20260831a1
Revises: zyw20260830a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "zyx20260831a1"
down_revision = "zyw20260830a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lembretes_contatos",
        sa.Column("lembrete_id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("produto_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("notification_queue_id", sa.BigInteger(), nullable=True),
        sa.Column("canal", sa.String(length=20), nullable=False),
        sa.Column("acao", sa.String(length=40), nullable=False),
        sa.Column(
            "status", sa.String(length=30), server_default="registrado", nullable=False
        ),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("resultado", sa.String(length=120), nullable=True),
        sa.Column("idempotency_key", sa.String(length=300), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lembrete_id"], ["lembretes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["notification_queue_id"],
            ["notification_queue.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["produto_id"], ["produtos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_lembretes_contatos_tenant_idempotency",
        ),
    )
    op.create_index(
        "ix_lembretes_contatos_tenant_id",
        "lembretes_contatos",
        ["tenant_id"],
    )
    op.create_index(
        "ix_lembretes_contatos_lembrete_id",
        "lembretes_contatos",
        ["lembrete_id"],
    )
    op.create_index(
        "ix_lembretes_contatos_tenant_lembrete_created",
        "lembretes_contatos",
        ["tenant_id", "lembrete_id", "created_at"],
    )
    op.create_index(
        "ix_lembretes_contatos_tenant_canal_created",
        "lembretes_contatos",
        ["tenant_id", "canal", "created_at"],
    )
    op.execute(sa.text("""
            INSERT INTO lembretes_contatos (
                lembrete_id,
                cliente_id,
                produto_id,
                usuario_id,
                notification_queue_id,
                canal,
                acao,
                status,
                mensagem,
                resultado,
                idempotency_key,
                tenant_id,
                created_at,
                updated_at
            )
            SELECT
                id,
                cliente_id,
                produto_id,
                NULL,
                NULL,
                'push',
                'notificacao_legada',
                'registrado',
                'Notificação registrada antes do histórico detalhado.',
                'Envio marcado no lembrete legado; entrega não confirmada.',
                'legacy_notification:' || tenant_id::text || ':' || id::text,
                tenant_id,
                COALESCE(data_notificacao_enviada, updated_at, now()),
                COALESCE(data_notificacao_enviada, updated_at, now())
            FROM lembretes
            WHERE notificacao_enviada IS TRUE
              AND data_notificacao_enviada IS NOT NULL
            """))


def downgrade() -> None:
    op.drop_table("lembretes_contatos")
