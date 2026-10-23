from fastapi import HTTPException, status
import pytest

from app.config import settings
from app.integrations.ifood.catalog import IfoodCatalogItem
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


def _preview_item(product_id, eligible, *, errors=(), warnings=()):
    return IfoodCatalogItem(
        product_id=product_id,
        sku=f"SKU-{product_id}",
        name=f"Produto {product_id}",
        eligible=eligible,
        payload={"barcode": str(product_id)} if eligible else None,
        errors=errors,
        warnings=warnings,
    )


@pytest.mark.parametrize("limit", [1, 50, 200])
def test_catalog_preview_exposes_late_eligible_product_before_limit(limit):
    # Loja grande: o unico produto selecionado fica apos milhares de rejeitados.
    items = [
        _preview_item(
            product_id,
            product_id == 6398,
            errors=() if product_id == 6398 else ("Nao selecionado",),
            warnings=("Conferir cadastro",) if product_id == 6398 else (),
        )
        for product_id in range(1, 7143)
    ]

    response = _catalog_response(items, limit=limit)

    assert response["items"][0]["product_id"] == 6398
    assert response["items"][0]["eligible"] is True
    assert len(response["items"]) == limit
    assert response["summary"] == {
        "total_scanned": 7142,
        "eligible": 1,
        "rejected": 7141,
    }
    assert response["issues"] == [{"message": "Nao selecionado", "count": 7141}]
    assert response["warnings"] == [{"message": "Conferir cadastro", "count": 1}]
    assert response["has_more"] is True


def test_catalog_preview_prioritization_preserves_issue_filter():
    response = _catalog_response(
        [
            _preview_item(1, False, errors=("Sem preco",)),
            _preview_item(2, True),
            _preview_item(3, False, errors=("Inativo",)),
            _preview_item(6398, True),
        ],
        limit=1,
        only_issues=True,
    )

    assert [item["product_id"] for item in response["items"]] == [1]
    assert response["summary"] == {"total_scanned": 4, "eligible": 2, "rejected": 2}
    assert response["issues"] == [
        {"message": "Sem preco", "count": 1},
        {"message": "Inativo", "count": 1},
    ]
    assert response["has_more"] is True


@pytest.mark.parametrize("only_issues", [False, True])
def test_catalog_preview_handles_empty_catalog(only_issues):
    assert _catalog_response([], limit=50, only_issues=only_issues) == {
        "summary": {"total_scanned": 0, "eligible": 0, "rejected": 0},
        "issues": [],
        "warnings": [],
        "items": [],
        "has_more": False,
    }


def test_catalog_preview_keeps_all_rejected_products_in_original_order():
    items = [
        _preview_item(product_id, False, errors=("Nao selecionado",))
        for product_id in (6398, 1, 9)
    ]

    response = _catalog_response(items, limit=50)

    assert [item["product_id"] for item in response["items"]] == [6398, 1, 9]
    assert response["summary"] == {"total_scanned": 3, "eligible": 0, "rejected": 3}
    assert response["has_more"] is False


def test_catalog_preview_preserves_order_within_eligible_and_rejected_groups():
    response = _catalog_response(
        [
            _preview_item(9, False),
            _preview_item(5, True),
            _preview_item(2, False),
            _preview_item(8, True),
        ],
        limit=50,
    )

    assert [item["product_id"] for item in response["items"]] == [5, 8, 9, 2]
    assert response["has_more"] is False
