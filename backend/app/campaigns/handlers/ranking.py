"""
Handler: Recálculo Mensal de Ranking
======================================

Disparo:  monthly_ranking_recalc (job mensal, dia 1 às 06:00)
Campanha: ranking_monthly

Lógica:
  1. Calcula o período de referência = mês anterior (ex: "2026-02")
  2. Para cada cliente do tenant, agrega:
     - total_spent: soma das vendas finalizadas nos últimos 12 meses
     - total_purchases: contagem de vendas nos últimos 12 meses
     - active_months: meses distintos com ao menos 1 compra (últimos 12 meses)
  3. Determina rank_level com base nos limites em campaign.params
  4. Usa INSERT INTO customer_rank_history ... ON CONFLICT DO NOTHING (idempotência)
  5. Para clientes que subiram de nível: enfileira notificação de upgrade

Parâmetros esperados em campaign.params:
  {
    "silver_min_spent": 300,    "silver_min_purchases": 4,   "silver_min_months": 2,
    "gold_min_spent": 1000,     "gold_min_purchases": 10,    "gold_min_months": 4,
    "diamond_min_spent": 3000,  "diamond_min_purchases": 20, "diamond_min_months": 6,
    "platinum_min_spent": 8000, "platinum_min_purchases": 40,"platinum_min_months": 10
  }
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import distinct, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.campaigns.models import (
    Campaign,
    CampaignEventQueue,
    CampaignTypeEnum,
    CustomerRankHistory,
    RankLevelEnum,
)
from app.campaigns.notification_service import enqueue_email

logger = logging.getLogger(__name__)

_SUPPORTED_EVENTS = frozenset({"monthly_ranking_recalc"})

# Hierarquia de níveis (ordem crescente)
_RANK_ORDER = [
    RankLevelEnum.bronze,
    RankLevelEnum.silver,
    RankLevelEnum.gold,
    RankLevelEnum.diamond,
    RankLevelEnum.platinum,
]


class RankingHandler:
    """Handler para recálculo mensal de ranking de clientes."""

    def run(
        self,
        db: Session,
        campaign: Campaign,
        event: CampaignEventQueue,
    ) -> dict:
        """
        Recalcula o ranking de todos os clientes do tenant.

        - Período de cálculo: últimos 12 meses (rolling window)
        - Período de referência: mês anterior (ex: "2026-02")
        - Idempotente: usa ON CONFLICT DO NOTHING
        - Notifica clientes que subiram de nível
        Não commita — o commit fica no CampaignEngine.
        """
        if event.event_type not in _SUPPORTED_EVENTS:
            return {"evaluated": 0, "rewarded": 0, "errors": 0}
        if campaign.campaign_type not in (
            CampaignTypeEnum.ranking_monthly, CampaignTypeEnum.monthly_highlight
        ):
            return {"evaluated": 0, "rewarded": 0, "errors": 0}

        from app.models import Cliente, User
        from app.vendas_models import Venda

        params = campaign.params or {}
        now = datetime.now(timezone.utc)
        # Período de referência = mês anterior
        first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month = (first_day_this_month - timedelta(days=1))
        period = last_month.strftime("%Y-%m")
        # Rolling window: últimos 12 meses
        window_start = first_day_this_month - timedelta(days=365)

        # Agrega métricas por cliente no tenant
        agg = (
            db.query(
                Venda.cliente_id,
                func.sum(Venda.total).label("total_spent"),
                func.count(Venda.id).label("total_purchases"),
                func.count(
                    distinct(func.date_trunc("month", Venda.data_finalizacao))
                ).label("active_months"),
            )
            .join(User, User.id == Venda.user_id)
            .filter(
                User.tenant_id == campaign.tenant_id,
                Venda.status == "finalizada",
                Venda.cliente_id.isnot(None),
                Venda.data_finalizacao >= window_start,
                Venda.data_finalizacao < first_day_this_month,
            )
            .group_by(Venda.cliente_id)
            .all()
        )

        evaluated = len(agg)
        rewarded = 0
        errors = 0

        for row in agg:
            try:
                total_spent = Decimal(str(row.total_spent or 0))
                total_purchases = row.total_purchases or 0
                active_months = row.active_months or 0

                new_rank = self._calculate_rank(
                    params=params,
                    total_spent=total_spent,
                    total_purchases=total_purchases,
                    active_months=active_months,
                )

                # Nível anterior (última entrada histórica)
                prev_row = (
                    db.query(CustomerRankHistory)
                    .filter(
                        CustomerRankHistory.tenant_id == campaign.tenant_id,
                        CustomerRankHistory.customer_id == row.cliente_id,
                        CustomerRankHistory.period < period,
                    )
                    .order_by(CustomerRankHistory.period.desc())
                    .first()
                )
                prev_rank = prev_row.rank_level if prev_row else RankLevelEnum.bronze

                # Insert idempotente (ON CONFLICT DO NOTHING)
                stmt = (
                    pg_insert(CustomerRankHistory)
                    .values(
                        tenant_id=campaign.tenant_id,
                        customer_id=row.cliente_id,
                        period=period,
                        rank_level=new_rank,
                        total_spent=total_spent,
                        total_purchases=total_purchases,
                        active_months=active_months,
                    )
                    .on_conflict_do_nothing(
                        constraint="uq_customer_rank_period"
                    )
                )
                db.execute(stmt)

                # Notifica upgrade de nível
                if _RANK_ORDER.index(new_rank) > _RANK_ORDER.index(prev_rank):
                    cliente = db.query(Cliente).filter(Cliente.id == row.cliente_id).first()
                    if cliente and cliente.email:
                        enqueue_email(
                            db,
                            tenant_id=campaign.tenant_id,
                            customer_id=row.cliente_id,
                            subject=f"Parabéns! Você subiu para o nível {new_rank.value.upper()} 🏆",
                            body=(
                                f"Olá, {cliente.nome}! Suas compras nos últimos meses "
                                f"te levaram para o nível {new_rank.value.upper()}. "
                                f"Aproveite os benefícios exclusivos!"
                            ),
                            email_address=cliente.email,
                            idempotency_key=(
                                f"rank_upgrade:{campaign.id}:{row.cliente_id}:{period}:email"
                            ),
                        )
                    rewarded += 1

            except Exception as exc:
                errors += 1
                logger.warning(
                    "[RankingHandler] Erro cliente_id=%s: %s", row.cliente_id, exc
                )

        logger.info(
            "[RankingHandler] tenant=%s period=%s avaliados=%d upgrades=%d erros=%d",
            campaign.tenant_id, period, evaluated, rewarded, errors,
        )
        return {"evaluated": evaluated, "rewarded": rewarded, "errors": errors}

    @staticmethod
    def _calculate_rank(
        params: dict,
        total_spent: Decimal,
        total_purchases: int,
        active_months: int,
    ) -> RankLevelEnum:
        """
        Determina o nível com base nos limiares configurados em campaign.params.
        Regra: cliente precisa atingir TODOS os critérios do nível para obtê-lo.
        Avalia do maior para o menor (platinum → bronze).
        """
        thresholds = [
            (
                RankLevelEnum.platinum,
                params.get("platinum_min_spent", 8000),
                params.get("platinum_min_purchases", 40),
                params.get("platinum_min_months", 10),
            ),
            (
                RankLevelEnum.diamond,
                params.get("diamond_min_spent", 3000),
                params.get("diamond_min_purchases", 20),
                params.get("diamond_min_months", 6),
            ),
            (
                RankLevelEnum.gold,
                params.get("gold_min_spent", 1000),
                params.get("gold_min_purchases", 10),
                params.get("gold_min_months", 4),
            ),
            (
                RankLevelEnum.silver,
                params.get("silver_min_spent", 300),
                params.get("silver_min_purchases", 4),
                params.get("silver_min_months", 2),
            ),
        ]
        for rank, min_spent, min_purchases, min_months in thresholds:
            if (
                total_spent >= Decimal(str(min_spent))
                and total_purchases >= int(min_purchases)
                and active_months >= int(min_months)
            ):
                return rank
        return RankLevelEnum.bronze
