from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.campaigns.handlers.cashback import CashbackHandler
from app.campaigns.handlers import cashback as cashback_module
from app.campaigns.models import (
    CampaignExecution,
    CampaignTypeEnum,
    CashbackTransaction,
    CustomerRankHistory,
    RankLevelEnum,
)
from app.vendas_models import Venda
from app.routes.app_mobile_funcionario_pdv.beneficios import (
    _calcular_beneficios_gerados_funcionario_pdv,
)


def test_cashback_uses_only_rank_percent_even_with_old_channel_bonus_saved(monkeypatch):
    db = MagicMock()
    venda_query = MagicMock()
    venda_query.filter.return_value.with_for_update.return_value.first.return_value = (
        SimpleNamespace(status="finalizada", total=Decimal("100.00"))
    )
    execution_query = MagicMock()
    execution_query.filter.return_value.first.return_value = None
    rank_query = MagicMock()
    rank_query.filter.return_value.order_by.return_value.first.return_value = (
        SimpleNamespace(rank_level=RankLevelEnum.gold)
    )
    db.query.side_effect = lambda model: {
        Venda: venda_query,
        CampaignExecution: execution_query,
        CustomerRankHistory: rank_query,
    }[model]
    monkeypatch.setattr(
        cashback_module, "lock_cashback_customer", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        cashback_module, "_notify_cashback_award", lambda *args, **kwargs: None
    )
    campaign = SimpleNamespace(
        id=10,
        tenant_id="11111111-1111-4111-8111-111111111111",
        campaign_type=CampaignTypeEnum.cashback,
        params={"gold_percent": 3, "pdv_bonus_percent": 2},
    )

    rewarded = CashbackHandler()._process(
        db=db,
        campaign=campaign,
        customer_id=12,
        venda_id=34,
        source_event_id=56,
        canal="loja_fisica",
    )

    assert rewarded == 1
    added = [call.args[0] for call in db.add.call_args_list]
    transaction = next(item for item in added if isinstance(item, CashbackTransaction))
    execution = next(item for item in added if isinstance(item, CampaignExecution))
    assert transaction.amount == Decimal("3.00")
    assert execution.reward_meta["percent"] == 3
    assert "bonus_percent" not in execution.reward_meta


def test_mobile_pdv_preview_uses_rank_percent_without_channel_bonus():
    db = MagicMock()
    campaign_query = MagicMock()
    campaign_query.filter.return_value.order_by.return_value.all.return_value = [
        SimpleNamespace(
            campaign_type=CampaignTypeEnum.cashback,
            name="Cashback Ouro",
            params={"gold_percent": 3, "pdv_bonus_percent": 2},
        )
    ]
    rank_query = MagicMock()
    rank_query.filter.return_value.order_by.return_value.first.return_value = (
        SimpleNamespace(rank_level=RankLevelEnum.gold)
    )
    db.query.side_effect = [campaign_query, rank_query]

    beneficios = _calcular_beneficios_gerados_funcionario_pdv(
        db,
        tenant_id="11111111-1111-4111-8111-111111111111",
        cliente_id=12,
        total_venda=100,
    )

    assert beneficios == [
        {
            "tipo": "cashback",
            "titulo": "Cashback Ouro",
            "valor": 3.0,
            "descricao": "3.00% sobre a venda",
            "cliente_id": 12,
        }
    ]
