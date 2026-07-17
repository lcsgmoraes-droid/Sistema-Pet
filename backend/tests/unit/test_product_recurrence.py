import inspect
from datetime import date, timedelta

from app.services.product_recurrence import (
    estimate_recurrence,
    notification_lead_days,
    process_finalized_sale_recurrence,
    run_due_recurrence_notifications,
)


def _dates(*intervals: int):
    values = [date(2026, 1, 1)]
    for interval in intervals:
        values.append(values[-1] + timedelta(days=interval))
    return values


def test_uses_configured_interval_until_history_is_sufficient():
    estimate = estimate_recurrence(
        _dates(30),
        configured_interval_days=45,
    )

    assert estimate.interval_days == 45
    assert estimate.source == "configurado"
    assert estimate.confidence == 0


def test_learns_stable_customer_repurchase_cycle():
    estimate = estimate_recurrence(
        _dates(29, 31, 30),
        configured_interval_days=45,
    )

    assert estimate.interval_days == 30
    assert estimate.source == "aprendido"
    assert estimate.confidence >= 0.65
    assert estimate.sample_count == 4


def test_discovers_unconfigured_recurring_product_only_with_confidence():
    learned = estimate_recurrence(_dates(14, 15))
    noisy = estimate_recurrence(_dates(10, 40))

    assert learned.interval_days == 14
    assert learned.source == "aprendido"
    assert noisy.interval_days is None
    assert noisy.source is None


def test_outlier_does_not_create_unsafe_automatic_prediction():
    estimate = estimate_recurrence(_dates(30, 30, 90))

    assert estimate.interval_days is None
    assert estimate.confidence < 0.65


def test_notification_lead_is_proportional_to_cycle():
    assert notification_lead_days(7) == 1
    assert notification_lead_days(30) == 7
    assert notification_lead_days(90) == 7


def test_finalized_sale_reloads_persisted_items_instead_of_cached_relationship():
    source = inspect.getsource(process_finalized_sale_recurrence)

    assert "db.query(VendaItem)" in source
    assert "VendaItem.venda_id == venda.id" in source
    assert 'getattr(venda, "itens", [])' not in source


def test_due_scheduler_registers_sale_model_and_counts_only_after_commit():
    source = inspect.getsource(run_due_recurrence_notifications)

    assert "from app.vendas_models import Venda" in source
    assert source.index("db.commit()") < source.index(
        'stats["queued"] += tenant_queued'
    )
