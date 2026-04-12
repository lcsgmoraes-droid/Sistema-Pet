from app.campaigns.loyalty_service import (
    build_loyalty_reward_refs,
    calculate_loyalty_available_stamps,
    calculate_loyalty_consumed_stamps,
    calculate_loyalty_stamp_count,
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


def test_calculate_loyalty_available_stamps_deducts_converted_cycles():
    assert calculate_loyalty_available_stamps(13, 1, 10) == 3
    assert calculate_loyalty_available_stamps(20, 2, 10) == 0
    assert calculate_loyalty_available_stamps(5, 1, 10) == 0
