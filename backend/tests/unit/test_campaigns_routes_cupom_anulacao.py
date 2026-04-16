from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.campaigns.models import Coupon, CouponStatusEnum
from app.campaigns.routes import anular_cupom


class _FakeQuery:
    def __init__(self, cupom):
        self._cupom = cupom

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._cupom


class _FakeDB:
    def __init__(self, cupom):
        self._cupom = cupom
        self.committed = False

    def query(self, model):
        if model is Coupon:
            return _FakeQuery(self._cupom)
        raise AssertionError(f"Modelo inesperado: {model}")

    def commit(self):
        self.committed = True


def test_anular_cupom_reverte_fidelidade_e_marca_voided():
    cupom = SimpleNamespace(
        id=101,
        tenant_id="tenant-1",
        code="FIEL-ABC",
        status=CouponStatusEnum.active,
    )
    db = _FakeDB(cupom)

    with patch(
        "app.campaigns.routes.revoke_loyalty_reward_by_coupon",
        return_value={"matched": True, "revoked": True},
    ) as revoke_mock:
        response = anular_cupom(
            code="FIEL-ABC",
            db=db,
            user_and_tenant=(1, "tenant-1"),
        )

    assert cupom.status == CouponStatusEnum.voided
    assert db.committed is True
    revoke_mock.assert_called_once_with(
        db,
        tenant_id="tenant-1",
        coupon_id=101,
        reason="cupom_anulado_manualmente",
    )
    assert response["ok"] is True
    assert response["status"] == "voided"
    assert response["fidelidade"]["cupom_vinculado"] is True
    assert response["fidelidade"]["carimbos_restaurados"] is True


def test_anular_cupom_rejeita_quando_nao_esta_ativo():
    cupom = SimpleNamespace(
        id=202,
        tenant_id="tenant-1",
        code="CUPOM-USADO",
        status=CouponStatusEnum.used,
    )
    db = _FakeDB(cupom)

    with patch("app.campaigns.routes.revoke_loyalty_reward_by_coupon") as revoke_mock:
        with pytest.raises(HTTPException) as exc:
            anular_cupom(
                code="CUPOM-USADO",
                db=db,
                user_and_tenant=(1, "tenant-1"),
            )

    assert exc.value.status_code == 400
    assert "Não é possível anular" in exc.value.detail
    revoke_mock.assert_not_called()
    assert db.committed is False
