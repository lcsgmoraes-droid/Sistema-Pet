from fastapi import HTTPException, status
import pytest

from app.config import settings
from app.integrations.ifood.client import IfoodClientError
from app.routes.ifood_integration_routes import _provider_http_status
from app.routes.ifood_integration_routes import _catalog_response
from app.routes.ifood_order_routes import _require_order_operations


def test_provider_auth_failure_is_not_exposed_as_corepet_session_failure():
    error = IfoodClientError("credenciais recusadas", status_code=401)

    assert _provider_http_status(error) == status.HTTP_502_BAD_GATEWAY


def test_provider_rate_limit_is_preserved_for_retry_feedback():
    error = IfoodClientError("limite atingido", status_code=429)

    assert _provider_http_status(error) == status.HTTP_429_TOO_MANY_REQUESTS


def test_catalog_response_can_focus_only_real_blockers():
    class Item:
        def __init__(self, eligible, errors=(), warnings=()):
            self.eligible = eligible
            self.errors = errors
            self.warnings = warnings

        def as_dict(self):
            return {"eligible": self.eligible, "errors": list(self.errors)}

    response = _catalog_response(
        [
            Item(True, warnings=("Sem EAN",)),
            Item(False, errors=("Sem preco",)),
            Item(False, errors=("Sem preco", "Inativo")),
        ],
        limit=50,
        only_issues=True,
    )

    assert response["summary"] == {"total_scanned": 3, "eligible": 1, "rejected": 2}
    assert response["items"] == [
        {"eligible": False, "errors": ["Sem preco"]},
        {"eligible": False, "errors": ["Sem preco", "Inativo"]},
    ]
    assert response["issues"][0] == {"message": "Sem preco", "count": 2}
    assert response["warnings"] == [{"message": "Sem EAN", "count": 1}]


def test_order_operations_remain_blocked_by_default(monkeypatch):
    monkeypatch.setattr(settings, "IFOOD_ORDER_OPERATIONS_ENABLED", False)

    with pytest.raises(HTTPException) as caught:
        _require_order_operations()

    assert caught.value.status_code == status.HTTP_409_CONFLICT
    assert "homologacao controlada" in caught.value.detail
