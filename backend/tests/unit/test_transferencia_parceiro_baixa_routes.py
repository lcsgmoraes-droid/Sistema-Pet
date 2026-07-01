from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import os

import pytest
from fastapi import HTTPException

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.estoque import transferencia_parceiro_baixa_routes as routes
from app.financeiro_models import LancamentoManual, Recebimento


class _FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed = True

    def flush(self):
        for index, item in enumerate(self.added, start=1):
            if getattr(item, "id", None) is None:
                item.id = index

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


def test_recebimento_individual_cria_lancamento_financeiro_e_dre(monkeypatch):
    conta = SimpleNamespace(
        id=126,
        status="pendente",
        valor_recebido=Decimal("0.00"),
        valor_final=Decimal("100.00"),
        data_recebimento=None,
        forma_pagamento_id=None,
        observacoes="",
        categoria_id=77,
        dre_subcategoria_id=88,
        canal="transferencia_parceiro",
        documento="TRP-126",
        cliente=SimpleNamespace(nome="Veterinaria Dra. Maiara"),
    )
    db = _FakeSession()
    dre_calls = []

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
    monkeypatch.setattr(
        routes,
        "_buscar_forma_pagamento_transferencia",
        lambda *_args, **_kwargs: SimpleNamespace(
            id=20,
            nome="Pix",
            tipo="pix",
            gera_contas_receber=False,
            conta_bancaria_destino_id=5,
        ),
    )
    monkeypatch.setattr(
        routes,
        "atualizar_dre_por_lancamento",
        lambda **kwargs: dre_calls.append(kwargs),
        raising=False,
    )

    payload = SimpleNamespace(
        valor_recebido=100,
        data_recebimento=date(2026, 7, 1),
        modo_baixa="recebimento",
        forma_pagamento_id=20,
        compensacoes=[],
        observacao="Pix recebido",
        devolver_estoque=False,
    )

    resultado = routes.registrar_recebimento_transferencia_parceiro.__wrapped__(
        126,
        payload,
        db=db,
        user_and_tenant=(SimpleNamespace(id=99), "tenant-1"),
    )

    recebimentos = [item for item in db.added if isinstance(item, Recebimento)]
    lancamentos = [item for item in db.added if isinstance(item, LancamentoManual)]

    assert resultado["modo_baixa"] == "recebimento"
    assert resultado["lancamento_financeiro_id"] == lancamentos[0].id
    assert len(recebimentos) == 1
    assert len(lancamentos) == 1
    assert recebimentos[0].data_recebimento == date(2026, 7, 1)
    assert lancamentos[0].valor == Decimal("100.00")
    assert lancamentos[0].data_lancamento == date(2026, 7, 1)
    assert lancamentos[0].status == "realizado"
    assert lancamentos[0].categoria_id == 77
    assert lancamentos[0].conta_bancaria_id == 5
    assert lancamentos[0].fornecedor_cliente == "Veterinaria Dra. Maiara"
    assert lancamentos[0].gerado_automaticamente is True
    assert dre_calls == [
        {
            "db": db,
            "tenant_id": "tenant-1",
            "dre_subcategoria_id": 88,
            "canal": "transferencia_parceiro",
            "valor": Decimal("100.00"),
            "data_lancamento": date(2026, 7, 1),
            "tipo_movimentacao": "RECEITA",
        }
    ]


def test_recebimento_individual_cartao_respeita_data_financeira(monkeypatch):
    conta = SimpleNamespace(
        id=127,
        status="pendente",
        valor_recebido=Decimal("0.00"),
        valor_final=Decimal("100.00"),
        data_recebimento=None,
        forma_pagamento_id=None,
        observacoes="",
        categoria_id=None,
        dre_subcategoria_id=None,
        canal="transferencia_parceiro",
        documento="TRP-127",
        cliente=SimpleNamespace(nome="Veterinaria Dra. Maiara"),
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
    monkeypatch.setattr(
        routes,
        "_buscar_forma_pagamento_transferencia",
        lambda *_args, **_kwargs: SimpleNamespace(
            id=21,
            nome="Cartao credito",
            tipo="cartao_credito",
            gera_contas_receber=True,
            prazo_recebimento=30,
            prazo_dias=30,
            dias_recebimento_antecipado=None,
            conta_bancaria_destino_id=None,
        ),
    )
    monkeypatch.setattr(
        routes,
        "atualizar_dre_por_lancamento",
        lambda **_kwargs: None,
        raising=False,
    )

    payload = SimpleNamespace(
        valor_recebido=100,
        data_recebimento=date(2026, 7, 1),
        modo_baixa="recebimento",
        forma_pagamento_id=21,
        compensacoes=[],
        observacao="Cartao recebido",
        devolver_estoque=False,
    )

    resultado = routes.registrar_recebimento_transferencia_parceiro.__wrapped__(
        127,
        payload,
        db=db,
        user_and_tenant=(SimpleNamespace(id=99), "tenant-1"),
    )

    recebimentos = [item for item in db.added if isinstance(item, Recebimento)]
    lancamentos = [item for item in db.added if isinstance(item, LancamentoManual)]

    assert resultado["data_recebimento"] == "2026-07-31"
    assert conta.data_recebimento == date(2026, 7, 31)
    assert recebimentos[0].data_recebimento == date(2026, 7, 31)
    assert lancamentos[0].data_lancamento == date(2026, 7, 31)


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
