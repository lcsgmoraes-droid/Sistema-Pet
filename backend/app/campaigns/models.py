"""
Modelos SQLAlchemy — Campaign Engine
======================================

Tabelas do motor de campanhas.

Princípios:
- Toda operação é idempotente (UNIQUE + ON CONFLICT DO NOTHING)
- Ledger cashback é fonte da verdade (imutável, append-only)
- Logs históricos são imutáveis — correção gera novo registro
- Todos os índices compostos têm tenant_id na primeira posição
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db import Base  # Base declarative já existente no projeto


# ---------------------------------------------------------------------------
# ENUMs
# ---------------------------------------------------------------------------

class EventOriginEnum(str, enum.Enum):
    user_action = "user_action"
    system_scheduled = "system_scheduled"
    campaign_action = "campaign_action"


class EventStatusEnum(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"
    skipped = "skipped"


class CampaignTypeEnum(str, enum.Enum):
    birthday_customer = "birthday_customer"
    birthday_pet = "birthday_pet"
    welcome_app = "welcome_app"
    welcome_ecommerce = "welcome_ecommerce"
    inactivity = "inactivity"
    loyalty_stamp = "loyalty_stamp"
    cashback = "cashback"
    ranking_monthly = "ranking_monthly"
    monthly_highlight = "monthly_highlight"
    quick_repurchase = "quick_repurchase"
    drawing = "drawing"
    bulk_segment = "bulk_segment"


class CampaignStatusEnum(str, enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"


class CouponTypeEnum(str, enum.Enum):
    percent = "percent"
    fixed = "fixed"
    gift = "gift"
    free_shipping = "free_shipping"


class CouponChannelEnum(str, enum.Enum):
    pdv = "pdv"
    app = "app"
    ecommerce = "ecommerce"
    all = "all"


class CouponStatusEnum(str, enum.Enum):
    active = "active"
    used = "used"
    expired = "expired"
    voided = "voided"


class RankLevelEnum(str, enum.Enum):
    bronze = "bronze"
    silver = "silver"
    gold = "gold"
    diamond = "diamond"
    platinum = "platinum"


class NotificationChannelEnum(str, enum.Enum):
    push = "push"
    email = "email"


class NotificationStatusEnum(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


class DrawingStatusEnum(str, enum.Enum):
    draft = "draft"
    open = "open"
    entries_frozen = "entries_frozen"
    drawn = "drawn"
    cancelled = "cancelled"


class CashbackSourceTypeEnum(str, enum.Enum):
    campaign = "campaign"
    manual = "manual"
    reversal = "reversal"


# ---------------------------------------------------------------------------
# Allowlist de event_types que entram no motor (proteção contra event storm)
# ---------------------------------------------------------------------------

CAMPAIGN_TRIGGER_EVENTS = frozenset({
    "purchase_completed",
    "customer_registered",
    "cpf_linked",
    "daily_birthday_check",
    "weekly_inactivity_check",
    "monthly_ranking_recalc",
    "drawing_execution",
})


# ---------------------------------------------------------------------------
# 1. campaign_event_queue — fila de eventos SKIP LOCKED
# ---------------------------------------------------------------------------

class CampaignEventQueue(Base):
    """
    Fila de eventos para o motor de campanhas.

    - status: pending → processing → done | failed | skipped
    - event_depth: 0 = gerado pelo usuário/sistema, >0 = derivado de campanha
    - Worker descarta event_depth > 1 e event_type fora de CAMPAIGN_TRIGGER_EVENTS
    - SKIP LOCKED garante que 2 workers não processem o mesmo evento
    """
    __tablename__ = "campaign_event_queue"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    event_type = Column(String(100), nullable=False)
    event_origin = Column(
        Enum(EventOriginEnum, name="campaign_event_origin_enum"),
        nullable=False,
        default=EventOriginEnum.user_action,
    )
    event_depth = Column(Integer, nullable=False, default=0)
    payload = Column(JSONB, nullable=False, default=dict)
    status = Column(
        Enum(EventStatusEnum, name="campaign_event_status_enum"),
        nullable=False,
        default=EventStatusEnum.pending,
    )
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    error_message = Column(Text, nullable=True)
    cursor_last_id = Column(BigInteger, nullable=True)  # Para jobs retomáveis
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_ceq_tenant_status_created", "tenant_id", "status", "created_at"),
        Index("ix_ceq_tenant_event_type", "tenant_id", "event_type"),
    )


# ---------------------------------------------------------------------------
# 2. campaigns — configuração de campanhas (parâmetros no banco, não em código)
# ---------------------------------------------------------------------------

class Campaign(Base):
    """
    Configuração de campanhas. Mudar parâmetro não exige deploy.

    - params: JSON livre para configurações específicas de cada tipo
      Ex: {"inactivity_days": 30, "coupon_value": 20.00}
    - priority: campanhas com menor número rodam primeiro no mesmo evento
    """
    __tablename__ = "campaigns"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    name = Column(String(200), nullable=False)
    campaign_type = Column(
        Enum(CampaignTypeEnum, name="campaign_type_enum"),
        nullable=False,
    )
    status = Column(
        Enum(CampaignStatusEnum, name="campaign_status_enum"),
        nullable=False,
        default=CampaignStatusEnum.active,
    )
    params = Column(JSONB, nullable=False, default=dict)
    priority = Column(Integer, nullable=False, default=100)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_campaigns_tenant_status", "tenant_id", "status"),
        Index("ix_campaigns_tenant_type", "tenant_id", "campaign_type"),
    )


# ---------------------------------------------------------------------------
# 3. campaign_executions — recompensas concedidas (imutável, idempotente)
# ---------------------------------------------------------------------------

class CampaignExecution(Base):
    """
    Registro imutável de cada recompensa concedida.

    UNIQUE(tenant_id, campaign_id, customer_id, reference_period) garante
    idempotência: executar o mesmo job duas vezes não duplica recompensas.

    - reference_period: string do período de referência.
      Ex: "2026-03" para mensal, "2026-03-04" para diário, "once" para único.
    - reward_type / reward_value: o que foi concedido
    - source_event_id: FK para campaign_event_queue (rastreabilidade)
    """
    __tablename__ = "campaign_executions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    campaign_id = Column(BigInteger, nullable=False)
    customer_id = Column(BigInteger, nullable=False)
    reference_period = Column(String(50), nullable=False)
    reward_type = Column(String(100), nullable=False)
    reward_value = Column(Numeric(12, 2), nullable=True)
    reward_meta = Column(JSONB, nullable=True)  # Dados extras (ex: coupon_id)
    source_event_id = Column(BigInteger, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "campaign_id", "customer_id", "reference_period",
            name="uq_campaign_execution_idempotency",
        ),
        Index(
            "ix_ce_tenant_campaign_customer",
            "tenant_id", "campaign_id", "customer_id",
        ),
        Index("ix_ce_tenant_customer_created", "tenant_id", "customer_id", "created_at"),
    )


# ---------------------------------------------------------------------------
# 4. campaign_run_log — resumo por execução de job
# ---------------------------------------------------------------------------

class CampaignRunLog(Base):
    """
    Resumo de cada execução de job. Imutável — não usar UPDATE.

    - evaluated: clientes avaliados
    - rewarded: clientes que receberam recompensa
    - errors: falhas individuais
    - cursor_last_id: último ID processado (para jobs retomáveis)
    """
    __tablename__ = "campaign_run_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    campaign_id = Column(BigInteger, nullable=False)
    run_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    event_type = Column(String(100), nullable=True)
    evaluated = Column(Integer, nullable=False, default=0)
    rewarded = Column(Integer, nullable=False, default=0)
    errors = Column(Integer, nullable=False, default=0)
    cursor_last_id = Column(BigInteger, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_crl_tenant_campaign_run", "tenant_id", "campaign_id", "run_at"),
    )


# ---------------------------------------------------------------------------
# 5. campaign_locks — mutex de campanhas
# ---------------------------------------------------------------------------

class CampaignLock(Base):
    """
    Mutex para garantir que apenas 1 worker execute um tipo de campanha
    por tenant ao mesmo tempo.

    PK composta (tenant_id, campaign_type). Worker tenta UPDATE expires_at;
    se o registro expirou ou não existe, assume o lock.
    """
    __tablename__ = "campaign_locks"

    tenant_id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    campaign_type = Column(String(100), primary_key=True, nullable=False)
    locked_by = Column(String(200), nullable=True)  # Ex: hostname:pid
    locked_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_cl_tenant_type_expires", "tenant_id", "campaign_type", "expires_at"),
    )


# ---------------------------------------------------------------------------
# 6. loyalty_stamps — carimbos de fidelidade
# ---------------------------------------------------------------------------

class LoyaltyStamp(Base):
    """
    Cada linha representa 1 carimbo ganho pelo cliente.

    UNIQUE(tenant_id, customer_id, venda_id) previne dupla contagem
    se a venda for reprocessada.

    - is_manual: carimbo lançado manualmente pelo operador (cartão físico)
    - campaign_execution_id: FK para rastreabilidade da recompensa gerada
    """
    __tablename__ = "loyalty_stamps"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    customer_id = Column(BigInteger, nullable=False)
    venda_id = Column(BigInteger, nullable=True)
    campaign_id = Column(BigInteger, nullable=False)
    is_manual = Column(Boolean, nullable=False, default=False)
    notes = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    voided_at = Column(DateTime(timezone=True), nullable=True)  # Estorno

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "customer_id", "venda_id",
            name="uq_loyalty_stamp_venda",
        ),
        Index("ix_ls_tenant_customer_created", "tenant_id", "customer_id", "created_at"),
        Index("ix_ls_tenant_campaign_customer", "tenant_id", "campaign_id", "customer_id"),
    )


# ---------------------------------------------------------------------------
# 7. cashback_transactions — ledger append-only
# ---------------------------------------------------------------------------

class CashbackTransaction(Base):
    """
    Ledger imutável de cashback. Saldo real = SUM(amount) por cliente.

    - source_type / source_id: referência à origem (campaign, manual, reversal)
    - amount: positivo = crédito, negativo = resgate/estorno
    - NUNCA fazer UPDATE nesta tabela — correção é um novo registro negativo
    """
    __tablename__ = "cashback_transactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    customer_id = Column(BigInteger, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    source_type = Column(
        Enum(CashbackSourceTypeEnum, name="cashback_source_type_enum"),
        nullable=False,
    )
    source_id = Column(BigInteger, nullable=True)  # campaign_execution_id ou outro
    description = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_ct_tenant_customer_created",
            "tenant_id", "customer_id", "created_at",
        ),
        Index("ix_ct_tenant_source", "tenant_id", "source_type", "source_id"),
    )


# ---------------------------------------------------------------------------
# 8. coupons — configuração de cupons
# ---------------------------------------------------------------------------

class Coupon(Base):
    """
    Cada cupom gerado pelo motor ou manualmente.

    - code: único por tenant (ex: ANIV2026-XK92)
    - campaign_id: FK opcional (cupons manuais não têm campanha)
    - customer_id: FK opcional (cupons nominais)
    - valid_until: NULL = indeterminado
    """
    __tablename__ = "coupons"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    code = Column(String(100), nullable=False)
    campaign_id = Column(BigInteger, nullable=True)
    customer_id = Column(BigInteger, nullable=True)
    coupon_type = Column(
        Enum(CouponTypeEnum, name="coupon_type_enum"),
        nullable=False,
    )
    discount_value = Column(Numeric(12, 2), nullable=True)
    discount_percent = Column(Numeric(5, 2), nullable=True)
    channel = Column(
        Enum(CouponChannelEnum, name="coupon_channel_enum"),
        nullable=False,
        default=CouponChannelEnum.all,
    )
    status = Column(
        Enum(CouponStatusEnum, name="coupon_status_enum"),
        nullable=False,
        default=CouponStatusEnum.active,
    )
    valid_until = Column(DateTime(timezone=True), nullable=True)
    min_purchase_value = Column(Numeric(12, 2), nullable=True)
    meta = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_coupon_code_tenant"),
        Index("ix_coupons_tenant_status", "tenant_id", "status"),
        Index("ix_coupons_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_coupons_tenant_campaign", "tenant_id", "campaign_id"),
    )


# ---------------------------------------------------------------------------
# 9. coupon_redemptions — uso real de cupons (append-only)
# ---------------------------------------------------------------------------

class CouponRedemption(Base):
    """
    Registro imutável de cada uso de cupom.

    - voided_at: não nulo = estorno. Nunca deletar o registro.
    - venda_id: venda onde o cupom foi aplicado
    """
    __tablename__ = "coupon_redemptions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    coupon_id = Column(BigInteger, nullable=False)
    customer_id = Column(BigInteger, nullable=True)
    venda_id = Column(BigInteger, nullable=True)
    discount_applied = Column(Numeric(12, 2), nullable=True)
    redeemed_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    voided_at = Column(DateTime(timezone=True), nullable=True)
    voided_reason = Column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_cr_tenant_coupon", "tenant_id", "coupon_id"),
        Index("ix_cr_tenant_customer_redeemed", "tenant_id", "customer_id", "redeemed_at"),
    )


# ---------------------------------------------------------------------------
# 10. customer_rank_history — histórico mensal de ranking
# ---------------------------------------------------------------------------

class CustomerRankHistory(Base):
    """
    Snapshot mensal do nível de cada cliente.

    - period: "2026-03" (ano-mês do cálculo)
    - rank_level: nível calculado naquele período
    - total_spent / total_purchases / active_months: métricas do período
    """
    __tablename__ = "customer_rank_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    customer_id = Column(BigInteger, nullable=False)
    period = Column(String(7), nullable=False)  # "2026-03"
    rank_level = Column(
        Enum(RankLevelEnum, name="rank_level_enum"),
        nullable=False,
        default=RankLevelEnum.bronze,
    )
    total_spent = Column(Numeric(14, 2), nullable=False, default=0)
    total_purchases = Column(Integer, nullable=False, default=0)
    active_months = Column(Integer, nullable=False, default=0)
    calculated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "customer_id", "period",
            name="uq_customer_rank_period",
        ),
        Index("ix_crh_tenant_period_rank", "tenant_id", "period", "rank_level"),
        Index("ix_crh_tenant_customer_period", "tenant_id", "customer_id", "period"),
    )


# ---------------------------------------------------------------------------
# 11. notification_queue — fila de envio
# ---------------------------------------------------------------------------

class NotificationQueue(Base):
    """
    Fila de notificações a enviar (push FCM + e-mail).

    - idempotency_key: garante que a mesma notificação não seja enfileirada
      mais de uma vez. Formato sugerido: "{campaign_execution_id}:{channel}"
    - status: pending → sent | failed | skipped
    - retry_count: até max_retries tentativas
    """
    __tablename__ = "notification_queue"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    idempotency_key = Column(String(300), nullable=False)
    customer_id = Column(BigInteger, nullable=False)
    channel = Column(
        Enum(NotificationChannelEnum, name="notification_channel_enum"),
        nullable=False,
    )
    subject = Column(String(500), nullable=True)  # Assunto do e-mail
    body = Column(Text, nullable=False)
    push_token = Column(String(500), nullable=True)
    email_address = Column(String(300), nullable=True)
    status = Column(
        Enum(NotificationStatusEnum, name="notification_status_enum"),
        nullable=False,
        default=NotificationStatusEnum.pending,
    )
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_notification_queue_idempotency",
        ),
        Index(
            "ix_nq_tenant_status_created",
            "tenant_id", "status", "created_at",
        ),
    )


# ---------------------------------------------------------------------------
# 12. notification_log — histórico de envios (imutável)
# ---------------------------------------------------------------------------

class NotificationLog(Base):
    """
    Histórico imutável de cada tentativa de envio.

    - idempotency_key: mesmo da fila — garante que o log não seja duplicado
    - provider_response: resposta do FCM / provedor de e-mail
    """
    __tablename__ = "notification_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    idempotency_key = Column(String(300), nullable=False)
    customer_id = Column(BigInteger, nullable=False)
    channel = Column(
        Enum(NotificationChannelEnum, name="notification_channel_enum"),
        nullable=False,
    )
    status = Column(String(50), nullable=False)  # sent / failed / skipped
    provider_response = Column(JSONB, nullable=True)
    sent_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_notification_log_idempotency",
        ),
        Index(
            "ix_nl_tenant_customer_sent",
            "tenant_id", "customer_id", "sent_at",
        ),
    )


# ---------------------------------------------------------------------------
# 13. drawings — sorteios
# ---------------------------------------------------------------------------

class Drawing(Base):
    """
    Sorteio auditável.

    - seed_uuid: semente aleatória fixada no momento do sorteio (auditoria)
    - entries_hash: SHA-256 da lista de participantes congelada
    - entries_frozen_at: momento em que a lista foi congelada (não aceita mais entradas)
    - winner_entry_id: FK para drawing_entries do ganhador
    """
    __tablename__ = "drawings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    campaign_id = Column(BigInteger, nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    rank_filter = Column(
        Enum(RankLevelEnum, name="rank_level_enum"),
        nullable=True,
    )  # NULL = todos os níveis
    status = Column(
        Enum(DrawingStatusEnum, name="drawing_status_enum"),
        nullable=False,
        default=DrawingStatusEnum.draft,
    )
    draw_date = Column(DateTime(timezone=True), nullable=True)
    entries_frozen_at = Column(DateTime(timezone=True), nullable=True)
    entries_hash = Column(String(64), nullable=True)  # SHA-256
    seed_uuid = Column(UUID(as_uuid=True), nullable=True)
    winner_entry_id = Column(BigInteger, nullable=True)
    prize_description = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_drawings_tenant_status", "tenant_id", "status"),
        Index("ix_drawings_tenant_campaign", "tenant_id", "campaign_id"),
    )


# ---------------------------------------------------------------------------
# 14. drawing_entries — participantes do sorteio
# ---------------------------------------------------------------------------

class DrawingEntry(Base):
    """
    Cada participante confirmado em um sorteio.

    - ticket_count: peso do participante (mais tickets = mais chances)
    """
    __tablename__ = "drawing_entries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    drawing_id = Column(BigInteger, nullable=False)
    customer_id = Column(BigInteger, nullable=False)
    ticket_count = Column(Integer, nullable=False, default=1)
    rank_level = Column(
        Enum(RankLevelEnum, name="rank_level_enum"),
        nullable=True,
    )
    registered_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "drawing_id", "customer_id",
            name="uq_drawing_entry_customer",
        ),
        Index("ix_de_tenant_drawing", "tenant_id", "drawing_id"),
    )


# ---------------------------------------------------------------------------
# Customer Merge Log — registro de unificações cross-canal
# ---------------------------------------------------------------------------

class CustomerMergeLog(Base):
    """
    Registra cada unificação de clientes feita via CPF/telefone/e-mail.
    O campo snapshot_json guarda os IDs das linhas movidas, permitindo desfazer.
    """
    __tablename__ = "customer_merge_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=False)
    customer_keep_id = Column(BigInteger, nullable=False)
    customer_remove_id = Column(BigInteger, nullable=False)
    motivo = Column(String(100), nullable=True)  # "mesmo_cpf" | "mesmo_telefone" | "manual"
    merged_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    merged_by_user_id = Column(Integer, nullable=True)
    snapshot_json = Column(JSONB, nullable=True)  # ids transferidos por tabela
    undone = Column(Boolean, nullable=False, default=False, server_default="false")
    undone_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_cml_tenant_keep", "tenant_id", "customer_keep_id"),
        Index("ix_cml_tenant_remove", "tenant_id", "customer_remove_id"),
    )
