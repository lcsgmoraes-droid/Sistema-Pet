from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.campaigns.loyalty_service import (
    build_loyalty_reward_refs,
    calculate_loyalty_available_stamps,
    calculate_loyalty_consumed_stamps,
    calculate_loyalty_signed_balance_components,
    calculate_loyalty_stamp_count,
    get_loyalty_balance_for_campaign,
    sync_loyalty_rewards_for_customer,
)


def test_calculate_loyalty_stamp_count_uses_floor_division():
    assert calculate_loyalty_stamp_count(49.90, 50) == 0
    assert calculate_loyalty_stamp_count(58, 50) == 1
    assert calculate_loyalty_stamp_count(98, 50) == 1
    assert calculate_loyalty_stamp_count(99.99, 50) == 1
    assert calculate_loyalty_stamp_count(100, 50) == 2


def test_build_loyalty_reward_refs_skips_intermediate_on_completed_cycle():
    refs = build_loyalty_reward_refs(
        total_stamps=10,
        stamps_to_complete=10,
        intermediate_stamp=5,
    )

    assert "cycle-1" in refs
    assert "mid-1" in refs
    assert "mid-2" not in refs


def test_calculate_loyalty_consumed_stamps_uses_completed_cycles():
    assert calculate_loyalty_consumed_stamps(0, 10) == 0
    assert calculate_loyalty_consumed_stamps(1, 10) == 10
    assert calculate_loyalty_consumed_stamps(2, 10) == 20


def test_calculate_loyalty_available_stamps_returns_signed_balance():
    assert calculate_loyalty_available_stamps(13, 1, 10) == 3
    assert calculate_loyalty_available_stamps(20, 2, 10) == 0
    assert calculate_loyalty_available_stamps(5, 1, 10) == -5


def test_calculate_loyalty_signed_balance_components_handles_debt():
    components = calculate_loyalty_signed_balance_components(
        total_stamps=5,
        committed_stamps=10,
    )

    assert components == {
        "raw_stamps": 5,
        "committed_stamps": 10,
        "available_stamps": -5,
        "visible_committed_stamps": 5,
        "debt_stamps": 5,
    }


def test_calculate_loyalty_signed_balance_components_handles_partial_conversion():
    components = calculate_loyalty_signed_balance_components(
        total_stamps=13,
        committed_stamps=10,
    )

    assert components == {
        "raw_stamps": 13,
        "committed_stamps": 10,
        "available_stamps": 3,
        "visible_committed_stamps": 10,
        "debt_stamps": 0,
    }


def test_get_loyalty_balance_reports_signed_debt_for_locked_reward():
    campaign = SimpleNamespace(
        id=1,
        tenant_id="tenant-1",
        params={"stamps_to_complete": 10},
    )
    execution = SimpleNamespace(
        reference_period="cycle-1",
        reward_meta={
            "consumed_stamps": 10,
            "stamps_to_complete_snapshot": 10,
        },
    )

    with (
        patch(
            "app.campaigns.loyalty_service.count_active_loyalty_stamps",
            return_value=5,
        ),
        patch(
            "app.campaigns.loyalty_service._load_loyalty_executions",
            return_value=[execution],
        ),
    ):
        balance = get_loyalty_balance_for_campaign(
            MagicMock(),
            campaign=campaign,
            customer_id=123,
        )

    assert balance == {
        "total_stamps": 5,
        "completed_cycles": 1,
        "consumed_stamps": 10,
        "committed_stamps": 10,
        "converted_stamps": 5,
        "available_stamps": -5,
        "debt_stamps": 5,
    }


def test_get_loyalty_balance_ignores_suppressed_cycle_placeholder():
    campaign = SimpleNamespace(
        id=1,
        tenant_id="tenant-1",
        params={"stamps_to_complete": 10},
    )
    execution = SimpleNamespace(
        reference_period="cycle-1",
        reward_meta={
            "revoked_after_use": True,
            "consumed_stamps": 0,
            "original_consumed_stamps": 10,
        },
    )

    with (
        patch(
            "app.campaigns.loyalty_service.count_active_loyalty_stamps",
            return_value=1,
        ),
        patch(
            "app.campaigns.loyalty_service._load_loyalty_executions",
            return_value=[execution],
        ),
    ):
        balance = get_loyalty_balance_for_campaign(
            MagicMock(),
            campaign=campaign,
            customer_id=123,
        )

    assert balance == {
        "total_stamps": 1,
        "completed_cycles": 0,
        "consumed_stamps": 0,
        "committed_stamps": 0,
        "converted_stamps": 0,
        "available_stamps": 1,
        "debt_stamps": 0,
    }


def test_sync_loyalty_rewards_does_not_reissue_suppressed_cycle_immediately():
    db = MagicMock()
    campaign = SimpleNamespace(
        id=1,
        tenant_id="tenant-1",
        name="Cartao Fidelidade",
        params={
            "stamps_to_complete": 10,
            "reward_type": "coupon",
            "reward_value": 25,
            "intermediate_stamp": 0,
        },
    )
    suppressed_execution = SimpleNamespace(
        reference_period="cycle-1",
        reward_meta={
            "revoked_after_use": True,
            "consumed_stamps": 0,
            "original_consumed_stamps": 10,
        },
    )

    with (
        patch(
            "app.campaigns.loyalty_service.count_active_loyalty_stamps",
            return_value=13,
        ),
        patch(
            "app.campaigns.loyalty_service._load_loyalty_executions",
            return_value=[suppressed_execution],
        ),
        patch(
            "app.campaigns.loyalty_service.get_loyalty_balance_for_campaign",
            return_value={
                "total_stamps": 13,
                "available_stamps": 13,
                "converted_stamps": 0,
                "debt_stamps": 0,
                "completed_cycles": 0,
            },
        ),
        patch("app.campaigns.loyalty_service._give_loyalty_reward") as give_reward,
        patch("app.campaigns.loyalty_service._revoke_loyalty_reward") as revoke_reward,
    ):
        result = sync_loyalty_rewards_for_customer(
            db,
            campaign=campaign,
            customer_id=123,
            source_event_id=None,
        )

    give_reward.assert_not_called()
    revoke_reward.assert_not_called()
    assert result["awarded"] == 0
    assert result["available_stamps"] == 13
