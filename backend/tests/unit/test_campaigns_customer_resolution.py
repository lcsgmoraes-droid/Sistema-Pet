from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.campaigns.routes import _resolver_customer_id_campanhas


def _mock_db_with_first_results(*results):
    query = MagicMock()
    query.filter.return_value = query
    query.first.side_effect = list(results)

    db = MagicMock()
    db.query.return_value = query
    return db


def test_resolver_customer_id_usa_codigo_quando_id_interno_nao_existe():
    db = _mock_db_with_first_results(None, SimpleNamespace(id=732, codigo="10001"))

    assert (
        _resolver_customer_id_campanhas(db, tenant_id="tenant-1", customer_ref=10001)
        == 732
    )


def test_resolver_customer_id_mantem_id_interno_quando_existe():
    db = _mock_db_with_first_results(SimpleNamespace(id=55, codigo="10001"))

    assert (
        _resolver_customer_id_campanhas(db, tenant_id="tenant-1", customer_ref=55) == 55
    )


def test_resolver_customer_id_rejeita_cliente_inexistente():
    db = _mock_db_with_first_results(None, None)

    with pytest.raises(HTTPException) as exc:
        _resolver_customer_id_campanhas(db, tenant_id="tenant-1", customer_ref=99999)

    assert exc.value.status_code == 404
    assert "Cliente nao encontrado" in exc.value.detail
