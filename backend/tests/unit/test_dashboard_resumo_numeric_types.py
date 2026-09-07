from decimal import Decimal
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.dashboard_routes import obter_resumo_dashboard, obter_entradas_saidas_por_dia


class _FakeQuery:
    def __init__(self, *, scalar=None, rows=None):
        self._scalar = scalar
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def options(self, *args, **kwargs):
        return self

    def group_by(self, *args, **kwargs):
        return self

    def scalar(self):
        return self._scalar

    def all(self):
        return self._rows or []


class _FakeSession:
    def __init__(self, queries):
        self._queries = iter(queries)

    def query(self, *args, **kwargs):
        return next(self._queries)


@pytest.mark.asyncio
@pytest.mark.parametrize("visao", ["venda", "recebimento"])
async def test_resumo_dashboard_normaliza_decimais_antes_dos_calculos(
    visao, monkeypatch
):
    monkeypatch.setattr(
        "app.dashboard_routes.montar_relatorio_recebimentos",
        lambda *args: {"resumo": {"total": 280, "recebimentos": 300, "devolucoes": 20}},
    )
    venda = SimpleNamespace(
        total=Decimal("150.00"),
        subtotal=Decimal("160.00"),
        desconto_valor=Decimal("10.00"),
        status="finalizada",
        pagamentos=[SimpleNamespace(valor=Decimal("120.00"))],
        itens=[
            SimpleNamespace(quantidade=Decimal("2.00")),
            SimpleNamespace(quantidade=Decimal("0.50")),
        ],
        rentabilidade_snapshot={"lucro": 33.75},
    )
    db = _FakeSession(
        [
            _FakeQuery(scalar=Decimal("500.00")),
            _FakeQuery(scalar=Decimal("125.50")),
            _FakeQuery(scalar=Decimal("200.00")),
            _FakeQuery(scalar=Decimal("10.00")),
            _FakeQuery(scalar=Decimal("15.00")),
            _FakeQuery(scalar=Decimal("300.00")),
            _FakeQuery(scalar=Decimal("20.00")),
            _FakeQuery(scalar=Decimal("25.00")),
            _FakeQuery(rows=[venda]),
            _FakeQuery(scalar=Decimal("40.25")),
            _FakeQuery(scalar=visao),
        ]
    )

    resumo = await obter_resumo_dashboard(
        periodo_dias=1,
        db=db,
        user_and_tenant=(SimpleNamespace(id=1), "tenant-1"),
    )

    assert resumo["saldo_atual"] == 374.5
    assert resumo["contas_receber"] == {
        "total": 200.0,
        "vencidas": 10.0,
        "vence_hoje": 15.0,
    }
    assert resumo["contas_pagar"] == {
        "total": 300.0,
        "vencidas": 20.0,
        "vence_hoje": 25.0,
    }
    assert resumo["vendas_periodo"]["unidades"] == 2.5
    assert resumo["vendas_periodo"]["lucro"] == 33.75
    assert resumo["visao_comercial"] == visao
    assert resumo["indicador_comercial"] == (280 if visao == "recebimento" else 160)
    assert resumo["fluxo_periodo"] == (
        {
            "entradas": 300.0,
            "saidas": 60.25,
            "lucro": 239.75,
        }
        if visao == "recebimento"
        else {
            "entradas": 120.0,
            "saidas": 40.25,
            "lucro": 79.75,
        }
    )


@pytest.mark.asyncio
async def test_grafico_recebimentos_usa_baixas_e_devolucoes_no_dia_do_movimento(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.dashboard_routes._intervalo_dias_calendario",
        lambda *args: (datetime(2026, 9, 1), datetime(2026, 9, 3)),
    )
    monkeypatch.setattr(
        "app.dashboard_routes.montar_relatorio_recebimentos",
        lambda *args: {
            "por_dia": [
                {"data": "2026-09-01", "entradas": 300, "devolucoes": 0},
                {"data": "2026-09-02", "entradas": 0, "devolucoes": 20},
            ]
        },
    )
    db = _FakeSession(
        [
            _FakeQuery(
                rows=[
                    SimpleNamespace(
                        data_venda=datetime(2026, 9, 2),
                        pagamentos=[SimpleNamespace(valor=999)],
                    )
                ]
            ),
            _FakeQuery(
                rows=[
                    SimpleNamespace(data=datetime(2026, 9, 2), total=Decimal("40.25"))
                ]
            ),
            _FakeQuery(scalar="recebimento"),
        ]
    )
    dados = await obter_entradas_saidas_por_dia(
        2, db, (SimpleNamespace(id=1), "tenant-1")
    )
    assert dados == [
        {"data": "2026-09-01", "entradas": 300, "saidas": 0},
        {"data": "2026-09-02", "entradas": 0, "saidas": 60.25},
    ]
