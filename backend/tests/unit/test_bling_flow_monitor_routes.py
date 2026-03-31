from types import SimpleNamespace

from app.bling_flow_monitor_routes import _mapa_numeros_notas_cache


class _FakeQuery:
    def __init__(self, resultado):
        self.resultado = resultado

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.resultado)


class _FakeDB:
    def __init__(self, resultado):
        self.resultado = resultado

    def query(self, model):
        return _FakeQuery(self.resultado)


def test_mapa_numeros_notas_cache_enriquece_nf_numero():
    db = _FakeDB(
        [
            SimpleNamespace(
                bling_id="25443301147",
                numero="011100",
                numero_pedido_loja="260331JFWD1VMB",
            )
        ]
    )

    mapa = _mapa_numeros_notas_cache(
        db,
        "tenant-1",
        [{"nf_bling_id": "25443301147"}],
    )

    assert mapa["25443301147"]["nf_numero"] == "011100"
    assert mapa["25443301147"]["numero_pedido_loja"] == "260331JFWD1VMB"
