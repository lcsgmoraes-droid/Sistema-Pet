from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.vendas.racao_previsao import (
    resolver_previsao_fim_racao,
    validar_previsao_fim_racao,
)
from app.vendas.schemas import VendaItemSchema


def _item_schema(**overrides):
    payload = {
        "tipo": "produto",
        "produto_id": 10,
        "quantidade": 1,
        "preco_unitario": 100,
        "subtotal": 100,
    }
    payload.update(overrides)
    return VendaItemSchema(**payload)


def test_schema_accepts_either_date_or_estimated_days():
    tomorrow = date.today() + timedelta(days=1)

    by_date = _item_schema(racao_data_prevista_fim=tomorrow)
    by_days = _item_schema(racao_prazo_estimado_dias=30)

    assert by_date.racao_data_prevista_fim == tomorrow
    assert by_date.racao_prazo_estimado_dias is None
    assert by_days.racao_prazo_estimado_dias == 30


def test_schema_rejects_two_choices_past_date_and_invalid_days():
    with pytest.raises(ValidationError):
        _item_schema(
            racao_data_prevista_fim=date.today() + timedelta(days=30),
            racao_prazo_estimado_dias=30,
        )
    with pytest.raises(ValidationError):
        _item_schema(racao_data_prevista_fim=date.today())
    with pytest.raises(ValidationError):
        _item_schema(racao_prazo_estimado_dias=366)


def test_prediction_requires_customer_and_feed_product():
    feed = SimpleNamespace(eh_racao=True)
    other_product = SimpleNamespace(eh_racao=False)
    item = {"racao_prazo_estimado_dias": 30}

    with pytest.raises(HTTPException, match="cliente"):
        validar_previsao_fim_racao(item, produto=feed, cliente_id=None)
    with pytest.raises(HTTPException, match="ração"):
        validar_previsao_fim_racao(item, produto=other_product, cliente_id=1)


def test_resolves_days_from_purchase_and_exact_date():
    purchase_at = datetime(2026, 8, 27, 14, 30)

    by_days = resolver_previsao_fim_racao(
        SimpleNamespace(
            racao_data_prevista_fim=None,
            racao_prazo_estimado_dias=30,
        ),
        data_compra=purchase_at,
    )
    by_date = resolver_previsao_fim_racao(
        SimpleNamespace(
            racao_data_prevista_fim=date(2026, 9, 10),
            racao_prazo_estimado_dias=None,
        ),
        data_compra=purchase_at,
    )

    assert by_days.data_prevista == datetime(2026, 9, 26, 14, 30)
    assert by_days.intervalo_dias == 30
    assert by_days.origem == "informado_venda_prazo"
    assert by_date.data_prevista == datetime(2026, 9, 10, 14, 30)
    assert by_date.intervalo_dias == 14
    assert by_date.origem == "informado_venda_data"


def test_past_exact_date_is_not_turned_into_a_reminder():
    resolved = resolver_previsao_fim_racao(
        SimpleNamespace(
            racao_data_prevista_fim=date(2026, 8, 26),
            racao_prazo_estimado_dias=None,
        ),
        data_compra=datetime(2026, 8, 27, 10, 0),
    )

    assert resolved is None
