"""create_campaign_engine_tables

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-03-04 00:00:00.000000

Cria todas as tabelas do motor de campanhas (Fase 1).

Tabelas criadas:
  1. campaign_event_queue  — fila de eventos SKIP LOCKED
  2. campaigns             — configuração de campanhas
  3. campaign_executions   — recompensas concedidas (idempotente)
  4. campaign_run_log      — resumo por execução de job
  5. campaign_locks        — mutex de campanhas
  6. loyalty_stamps        — carimbos de fidelidade
  7. cashback_transactions — ledger append-only
  8. coupons               — configuração de cupons
  9. coupon_redemptions    — uso real de cupons
 10. customer_rank_history — histórico mensal de ranking
 11. notification_queue    — fila de envio (push + e-mail)
 12. notification_log      — histórico de envios
 13. drawings              — sorteios auditáveis
 14. drawing_entries       — participantes de sorteio

Princípios:
- Todos os índices são compostos com tenant_id na primeira posição
- UNIQUE constraints garantem idempotência
- Nenhum dado de lógica de campanha em código — apenas configuração no banco
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ENUMs — criar primeiro para usar nas tabelas
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE campaign_event_origin_enum AS ENUM (
                'user_action', 'system_scheduled', 'campaign_action'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE campaign_event_status_enum AS ENUM (
                'pending', 'processing', 'done', 'failed', 'skipped'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE campaign_type_enum AS ENUM (
                'birthday_customer', 'birthday_pet',
                'welcome_app', 'welcome_ecommerce',
                'inactivity', 'loyalty_stamp', 'cashback',
                'ranking_monthly', 'monthly_highlight',
                'quick_repurchase', 'drawing', 'bulk_segment'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE campaign_status_enum AS ENUM (
                'active', 'paused', 'archived'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE coupon_type_enum AS ENUM (
                'percent', 'fixed', 'gift', 'free_shipping'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE coupon_channel_enum AS ENUM (
                'pdv', 'app', 'ecommerce', 'all'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE coupon_status_enum AS ENUM (
                'active', 'used', 'expired', 'voided'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE rank_level_enum AS ENUM (
                'bronze', 'silver', 'gold', 'diamond', 'platinum'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notification_channel_enum AS ENUM (
                'push', 'email'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notification_status_enum AS ENUM (
                'pending', 'sent', 'failed', 'skipped'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE drawing_status_enum AS ENUM (
                'draft', 'open', 'entries_frozen', 'drawn', 'cancelled'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE cashback_source_type_enum AS ENUM (
                'campaign', 'manual', 'reversal'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    # ------------------------------------------------------------------
    # 1. campaign_event_queue
    # ------------------------------------------------------------------
    op.create_table(
        "campaign_event_queue",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column(
            "event_origin",
            postgresql.ENUM(
                "user_action", "system_scheduled", "campaign_action",
                name="campaign_event_origin_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="user_action",
        ),
        sa.Column("event_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "processing", "done", "failed", "skipped",
                name="campaign_event_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cursor_last_id", sa.BigInteger(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ceq_tenant_status_created",
        "campaign_event_queue",
        ["tenant_id", "status", "created_at"],
    )
    op.create_index(
        "ix_ceq_tenant_event_type",
        "campaign_event_queue",
        ["tenant_id", "event_type"],
    )

    # ------------------------------------------------------------------
    # 2. campaigns
    # ------------------------------------------------------------------
    op.create_table(
        "campaigns",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "campaign_type",
            postgresql.ENUM(
                "birthday_customer", "birthday_pet",
                "welcome_app", "welcome_ecommerce",
                "inactivity", "loyalty_stamp", "cashback",
                "ranking_monthly", "monthly_highlight",
                "quick_repurchase", "drawing", "bulk_segment",
                name="campaign_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active", "paused", "archived",
                name="campaign_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaigns_tenant_status", "campaigns", ["tenant_id", "status"])
    op.create_index("ix_campaigns_tenant_type", "campaigns", ["tenant_id", "campaign_type"])

    # ------------------------------------------------------------------
    # 3. campaign_executions
    # ------------------------------------------------------------------
    op.create_table(
        "campaign_executions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("reference_period", sa.String(50), nullable=False),
        sa.Column("reward_type", sa.String(100), nullable=False),
        sa.Column("reward_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("reward_meta", postgresql.JSONB(), nullable=True),
        sa.Column("source_event_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "campaign_id", "customer_id", "reference_period",
            name="uq_campaign_execution_idempotency",
        ),
    )
    op.create_index(
        "ix_ce_tenant_campaign_customer",
        "campaign_executions",
        ["tenant_id", "campaign_id", "customer_id"],
    )
    op.create_index(
        "ix_ce_tenant_customer_created",
        "campaign_executions",
        ["tenant_id", "customer_id", "created_at"],
    )

    # ------------------------------------------------------------------
    # 4. campaign_run_log
    # ------------------------------------------------------------------
    op.create_table(
        "campaign_run_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("event_type", sa.String(100), nullable=True),
        sa.Column("evaluated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rewarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cursor_last_id", sa.BigInteger(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crl_tenant_campaign_run",
        "campaign_run_log",
        ["tenant_id", "campaign_id", "run_at"],
    )

    # ------------------------------------------------------------------
    # 5. campaign_locks
    # ------------------------------------------------------------------
    op.create_table(
        "campaign_locks",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_type", sa.String(100), nullable=False),
        sa.Column("locked_by", sa.String(200), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "campaign_type"),
    )
    op.create_index(
        "ix_cl_tenant_type_expires",
        "campaign_locks",
        ["tenant_id", "campaign_type", "expires_at"],
    )

    # ------------------------------------------------------------------
    # 6. loyalty_stamps
    # ------------------------------------------------------------------
    op.create_table(
        "loyalty_stamps",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("venda_id", sa.BigInteger(), nullable=True),
        sa.Column("campaign_id", sa.BigInteger(), nullable=False),
        sa.Column("is_manual", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "customer_id", "venda_id",
            name="uq_loyalty_stamp_venda",
        ),
    )
    op.create_index(
        "ix_ls_tenant_customer_created",
        "loyalty_stamps",
        ["tenant_id", "customer_id", "created_at"],
    )
    op.create_index(
        "ix_ls_tenant_campaign_customer",
        "loyalty_stamps",
        ["tenant_id", "campaign_id", "customer_id"],
    )

    # ------------------------------------------------------------------
    # 7. cashback_transactions
    # ------------------------------------------------------------------
    op.create_table(
        "cashback_transactions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "source_type",
            postgresql.ENUM(
                "campaign", "manual", "reversal",
                name="cashback_source_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("source_id", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ct_tenant_customer_created",
        "cashback_transactions",
        ["tenant_id", "customer_id", "created_at"],
    )
    op.create_index(
        "ix_ct_tenant_source",
        "cashback_transactions",
        ["tenant_id", "source_type", "source_id"],
    )

    # ------------------------------------------------------------------
    # 8. coupons
    # ------------------------------------------------------------------
    op.create_table(
        "coupons",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("campaign_id", sa.BigInteger(), nullable=True),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "coupon_type",
            postgresql.ENUM(
                "percent", "fixed", "gift", "free_shipping",
                name="coupon_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("discount_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "channel",
            postgresql.ENUM(
                "pdv", "app", "ecommerce", "all",
                name="coupon_channel_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="all",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active", "used", "expired", "voided",
                name="coupon_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("min_purchase_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_coupon_code_tenant"),
    )
    op.create_index("ix_coupons_tenant_status", "coupons", ["tenant_id", "status"])
    op.create_index("ix_coupons_tenant_customer", "coupons", ["tenant_id", "customer_id"])
    op.create_index("ix_coupons_tenant_campaign", "coupons", ["tenant_id", "campaign_id"])

    # ------------------------------------------------------------------
    # 9. coupon_redemptions
    # ------------------------------------------------------------------
    op.create_table(
        "coupon_redemptions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coupon_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column("venda_id", sa.BigInteger(), nullable=True),
        sa.Column("discount_applied", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "redeemed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_reason", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cr_tenant_coupon",
        "coupon_redemptions",
        ["tenant_id", "coupon_id"],
    )
    op.create_index(
        "ix_cr_tenant_customer_redeemed",
        "coupon_redemptions",
        ["tenant_id", "customer_id", "redeemed_at"],
    )

    # ------------------------------------------------------------------
    # 10. customer_rank_history
    # ------------------------------------------------------------------
    op.create_table(
        "customer_rank_history",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column(
            "rank_level",
            postgresql.ENUM(
                "bronze", "silver", "gold", "diamond", "platinum",
                name="rank_level_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="bronze",
        ),
        sa.Column("total_spent", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_purchases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "customer_id", "period",
            name="uq_customer_rank_period",
        ),
    )
    op.create_index(
        "ix_crh_tenant_period_rank",
        "customer_rank_history",
        ["tenant_id", "period", "rank_level"],
    )
    op.create_index(
        "ix_crh_tenant_customer_period",
        "customer_rank_history",
        ["tenant_id", "customer_id", "period"],
    )

    # ------------------------------------------------------------------
    # 11. notification_queue
    # ------------------------------------------------------------------
    op.create_table(
        "notification_queue",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(300), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "channel",
            postgresql.ENUM(
                "push", "email",
                name="notification_channel_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("push_token", sa.String(500), nullable=True),
        sa.Column("email_address", sa.String(300), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "sent", "failed", "skipped",
                name="notification_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_notification_queue_idempotency"),
    )
    op.create_index(
        "ix_nq_tenant_status_created",
        "notification_queue",
        ["tenant_id", "status", "created_at"],
    )

    # ------------------------------------------------------------------
    # 12. notification_log
    # ------------------------------------------------------------------
    op.create_table(
        "notification_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(300), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "channel",
            postgresql.ENUM(
                "push", "email",
                name="notification_channel_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("provider_response", postgresql.JSONB(), nullable=True),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_notification_log_idempotency"),
    )
    op.create_index(
        "ix_nl_tenant_customer_sent",
        "notification_log",
        ["tenant_id", "customer_id", "sent_at"],
    )

    # ------------------------------------------------------------------
    # 13. drawings
    # ------------------------------------------------------------------
    op.create_table(
        "drawings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "rank_filter",
            postgresql.ENUM(
                "bronze", "silver", "gold", "diamond", "platinum",
                name="rank_level_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft", "open", "entries_frozen", "drawn", "cancelled",
                name="drawing_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("draw_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entries_frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entries_hash", sa.String(64), nullable=True),
        sa.Column("seed_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("winner_entry_id", sa.BigInteger(), nullable=True),
        sa.Column("prize_description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drawings_tenant_status", "drawings", ["tenant_id", "status"])
    op.create_index("ix_drawings_tenant_campaign", "drawings", ["tenant_id", "campaign_id"])

    # ------------------------------------------------------------------
    # 14. drawing_entries
    # ------------------------------------------------------------------
    op.create_table(
        "drawing_entries",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("drawing_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("ticket_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "rank_level",
            postgresql.ENUM(
                "bronze", "silver", "gold", "diamond", "platinum",
                name="rank_level_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "drawing_id", "customer_id",
            name="uq_drawing_entry_customer",
        ),
    )
    op.create_index(
        "ix_de_tenant_drawing",
        "drawing_entries",
        ["tenant_id", "drawing_id"],
    )


def downgrade() -> None:
    # Remover tabelas na ordem inversa (dependências)
    op.drop_table("drawing_entries")
    op.drop_table("drawings")
    op.drop_table("notification_log")
    op.drop_table("notification_queue")
    op.drop_table("customer_rank_history")
    op.drop_table("coupon_redemptions")
    op.drop_table("coupons")
    op.drop_table("cashback_transactions")
    op.drop_table("loyalty_stamps")
    op.drop_table("campaign_locks")
    op.drop_table("campaign_run_log")
    op.drop_table("campaign_executions")
    op.drop_table("campaigns")
    op.drop_table("campaign_event_queue")

    # Remover ENUMs
    op.execute("DROP TYPE IF EXISTS drawing_status_enum")
    op.execute("DROP TYPE IF EXISTS cashback_source_type_enum")
    op.execute("DROP TYPE IF EXISTS notification_status_enum")
    op.execute("DROP TYPE IF EXISTS notification_channel_enum")
    op.execute("DROP TYPE IF EXISTS rank_level_enum")
    op.execute("DROP TYPE IF EXISTS coupon_status_enum")
    op.execute("DROP TYPE IF EXISTS coupon_channel_enum")
    op.execute("DROP TYPE IF EXISTS coupon_type_enum")
    op.execute("DROP TYPE IF EXISTS campaign_status_enum")
    op.execute("DROP TYPE IF EXISTS campaign_type_enum")
    op.execute("DROP TYPE IF EXISTS campaign_event_status_enum")
    op.execute("DROP TYPE IF EXISTS campaign_event_origin_enum")
