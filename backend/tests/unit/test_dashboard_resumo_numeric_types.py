from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.dashboard_routes import obter_resumo_dashboard


class _FakeQuery:
    def __init__(self, *, scalar=None, rows=None):
        self._scalar = scalar
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def options(self, *args, **kwargs):
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
async def test_resumo_dashboard_normaliza_decimais_antes_dos_calculos():
    venda = SimpleNamespace(
        total=Decimal("150.00"),
        subtotal=Decimal("160.00"),
        desconto_valor=Decimal("10.00"),
        status="finalizada",
        pagamentos=[SimpleNamespace(valor=Decimal("120.00"))],
    )
    db = _FakeSession(
        [
            _FakeQuery(scalar=Decimal("500.00")),
            _FakeQuery(scalar=Decimal("125.50")),
            _FakeQuery(scalar=Decimal("200.00")),
            _FakeQuery(scalar=Decimal("10.00")),
            _FakeQuery(scalar=Decimal("300.00")),
            _FakeQuery(scalar=Decimal("20.00")),
            _FakeQuery(rows=[venda]),
            _FakeQuery(scalar=Decimal("40.25")),
        ]
    )

    resumo = await obter_resumo_dashboard(
        periodo_dias=1,
        db=db,
        user_and_tenant=(SimpleNamespace(id=1), "tenant-1"),
    )

    assert resumo["saldo_atual"] == 374.5
    assert resumo["contas_receber"] == {"total": 200.0, "vencidas": 10.0}
    assert resumo["contas_pagar"] == {"total": 300.0, "vencidas": 20.0}
    assert resumo["fluxo_periodo"] == {
        "entradas": 120.0,
        "saidas": 40.25,
        "lucro": 79.75,
    }
