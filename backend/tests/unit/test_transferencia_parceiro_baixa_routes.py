from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import os

import pytest
from fastapi import HTTPException

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.estoque import transferencia_parceiro_baixa_routes as routes


class _FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed = True

    def refresh(self, _item):
        return None


def test_acerto_individual_exige_compensacao_real(monkeypatch):
    conta = SimpleNamespace(
        id=123,
        status="pendente",
        valor_recebido=Decimal("0.00"),
        valor_final=Decimal("100.00"),
        data_recebimento=None,
        forma_pagamento_id=None,
        observacoes="",
    )

    monkeypatch.setattr(
        routes, "_buscar_conta_transferencia_parceiro", lambda *_args: conta
    )
    monkeypatch.setattr(routes, "_saldo_conta_receber", lambda _conta: 100.0)
    monkeypatch.setattr(
        routes,
        "_obter_ou_criar_forma_pagamento_acerto",
        lambda *_args, **_kwargs: SimpleNamespace(id=10, nome="Acerto"),
    )
    monkeypatch.setattr(
        routes,
        "_status_transferencia_parceiro",
        lambda _conta: ("recebido", "Recebido"),
    )

    payload = SimpleNamespace(
        valor_recebido=100,
        data_recebimento=date(2026, 7, 1),
        modo_baixa="acerto",
        forma_pagamento_id=None,
        compensacoes=[],
        observacao=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        routes.registrar_recebimento_transferencia_parceiro.__wrapped__(
            123,
            payload,
            db=_FakeSession(),
            user_and_tenant=(SimpleNamespace(id=99), "tenant-1"),
        )

    assert exc_info.value.status_code == 400
    assert "compensar" in exc_info.value.detail.lower()
