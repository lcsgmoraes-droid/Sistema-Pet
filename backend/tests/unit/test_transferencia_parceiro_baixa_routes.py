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


def test_produto_devolvido_individual_sem_estoque_nao_cria_recebimento(monkeypatch):
    conta = SimpleNamespace(
        id=124,
        status="pendente",
        valor_recebido=Decimal("0.00"),
        valor_final=Decimal("100.00"),
        data_recebimento=None,
        forma_pagamento_id=None,
        observacoes="",
    )
    db = _FakeSession()

    monkeypatch.setattr(
        routes, "_buscar_conta_transferencia_parceiro", lambda *_args: conta
    )
    monkeypatch.setattr(
        routes,
        "_saldo_conta_receber",
        lambda conta: round(
            max(float(conta.valor_final or 0) - float(conta.valor_recebido or 0), 0),
            2,
        ),
    )
    monkeypatch.setattr(
        routes,
        "_status_transferencia_parceiro",
        lambda _conta: ("recebido", "Recebido"),
    )

    payload = SimpleNamespace(
        valor_recebido=100,
        data_recebimento=date(2026, 7, 1),
        modo_baixa="produto_devolvido",
        forma_pagamento_id=None,
        compensacoes=[],
        observacao="Produto retornou sem entrada fisica no estoque.",
        devolver_estoque=False,
    )

    resultado = routes.registrar_recebimento_transferencia_parceiro.__wrapped__(
        124,
        payload,
        db=db,
        user_and_tenant=(SimpleNamespace(id=99), "tenant-1"),
    )

    assert resultado["modo_baixa"] == "produto_devolvido"
    assert resultado["valor_recebido"] == 100.0
    assert resultado["saldo_aberto"] == 0
    assert db.committed is True
    assert db.added == []


def test_produto_devolvido_individual_com_estoque_exige_baixa_integral(monkeypatch):
    conta = SimpleNamespace(
        id=125,
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

    payload = SimpleNamespace(
        valor_recebido=50,
        data_recebimento=date(2026, 7, 1),
        modo_baixa="produto_devolvido",
        forma_pagamento_id=None,
        compensacoes=[],
        observacao="Produto voltou para estoque.",
        devolver_estoque=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        routes.registrar_recebimento_transferencia_parceiro.__wrapped__(
            125,
            payload,
            db=_FakeSession(),
            user_and_tenant=(SimpleNamespace(id=99), "tenant-1"),
        )

    assert exc_info.value.status_code == 400
    assert "baixa integral" in exc_info.value.detail.lower()
