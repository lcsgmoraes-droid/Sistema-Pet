import inspect
from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.produtos.schemas import ProdutoProtocoloRecorrenciaSchema
from app.services.product_recurrence import (
    estimate_recurrence,
    calculate_next_protocol_step,
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


def test_keeps_short_configured_interval_for_continuous_repurchase():
    estimate = estimate_recurrence([], configured_interval_days=2)

    assert estimate.interval_days == 2
    assert estimate.source == "configurado"


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


def test_protocol_doses_stay_anchored_to_first_sale():
    started_at = datetime(2026, 9, 1, 10, 0)
    bought_early = datetime(2026, 9, 12, 10, 0)

    next_step = calculate_next_protocol_step(
        [0, 14, 21],
        completed_dose=2,
        protocol_start_at=started_at,
        completed_at=bought_early,
        restart_after_days=180,
    )

    assert next_step is not None
    assert next_step.kind == "proxima_dose"
    assert next_step.dose_number == 3
    assert next_step.due_at == datetime(2026, 9, 22, 10, 0)


def test_protocol_can_offer_a_new_cycle_after_last_dose():
    completed_at = datetime(2026, 9, 22, 10, 0)

    next_step = calculate_next_protocol_step(
        [0, 14, 21],
        completed_dose=3,
        protocol_start_at=datetime(2026, 9, 1, 10, 0),
        completed_at=completed_at,
        restart_after_days=180,
    )

    assert next_step is not None
    assert next_step.kind == "reinicio_protocolo"
    assert next_step.dose_number == 1
    assert next_step.due_at == completed_at + timedelta(days=180)


def test_protocol_ends_without_reminder_when_restart_is_empty():
    assert (
        calculate_next_protocol_step(
            [0],
            completed_dose=1,
            protocol_start_at=datetime(2026, 9, 1, 10, 0),
            completed_at=datetime(2026, 9, 1, 10, 0),
        )
        is None
    )


def test_protocol_schema_accepts_offsets_from_sale_day():
    protocol = ProdutoProtocoloRecorrenciaSchema(
        nome="Vacina filhote",
        tipo="protocolo_doses",
        fase_vida="puppy",
        reiniciar_apos_dias=180,
        doses=[
            {"numero_dose": 1, "dias_desde_inicio": 0},
            {"numero_dose": 2, "dias_desde_inicio": 14},
            {"numero_dose": 3, "dias_desde_inicio": 21},
        ],
    )

    assert [dose.dias_desde_inicio for dose in protocol.doses] == [0, 14, 21]
    assert protocol.reiniciar_apos_dias == 180


def test_protocol_schema_rejects_non_increasing_offsets():
    with pytest.raises(ValidationError, match="dias das doses devem ser crescentes"):
        ProdutoProtocoloRecorrenciaSchema(
            nome="Vacina filhote",
            tipo="protocolo_doses",
            doses=[
                {"numero_dose": 1, "dias_desde_inicio": 0},
                {"numero_dose": 2, "dias_desde_inicio": 14},
                {"numero_dose": 3, "dias_desde_inicio": 14},
            ],
        )


def test_finalized_sale_reloads_persisted_items_instead_of_cached_relationship():
    source = inspect.getsource(process_finalized_sale_recurrence)

    assert "db.query(VendaItem)" in source
    assert "VendaItem.venda_id == venda.id" in source
    assert 'getattr(venda, "itens", [])' not in source


def test_due_scheduler_registers_sale_model_and_counts_only_after_commit():
    source = inspect.getsource(run_due_recurrence_notifications)

    assert "from app.vendas_models import Venda" in source
    assert "resolve_customer_app_user_id" in source
    assert "User.email == customer_email" not in source
    assert source.index("db.commit()") < source.index(
        'stats["queued"] += tenant_queued'
    )
