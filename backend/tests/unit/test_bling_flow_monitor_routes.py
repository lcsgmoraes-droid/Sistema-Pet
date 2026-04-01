from types import SimpleNamespace

from app.bling_flow_monitor_routes import _enriquecer_registros_contexto, _mapa_numeros_notas_cache


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


def test_mapa_numeros_notas_cache_usa_payload_quando_coluna_numero_vem_vazia():
    db = _FakeDB(
        [
            SimpleNamespace(
                bling_id="25443301148",
                numero=None,
                numero_pedido_loja="260331JFWD1VMB",
                detalhe_payload={"numero": "011101"},
                resumo_payload={},
            )
        ]
    )

    mapa = _mapa_numeros_notas_cache(
        db,
        "tenant-1",
        [{"nf_bling_id": "25443301148"}],
    )

    assert mapa["25443301148"]["nf_numero"] == "011101"


def test_enriquecer_registros_contexto_inclui_nf_humana_e_dados_de_duplicidade(monkeypatch):
    monkeypatch.setattr(
        "app.bling_flow_monitor_routes._mapa_numeros_pedidos",
        lambda db, tenant_id, registros: {
            (10, "25439737683"): {
                "pedido_bling_numero": "11680",
                "numero_pedido_loja": "260330GDQVHGXX",
                "nf_numero": None,
                "pedido_status_atual": "confirmado",
            }
        },
    )
    monkeypatch.setattr(
        "app.bling_flow_monitor_routes._mapa_numeros_notas_cache",
        lambda db, tenant_id, registros: {
            "25443301147": {
                "nf_numero": "011100",
                "numero_pedido_loja": "260330GDQVHGXX",
            }
        },
    )
    monkeypatch.setattr(
        "app.bling_flow_monitor_routes.mapear_duplicidade_por_pedido_ids",
        lambda db, tenant_id, pedido_ids: {
            10: {
                "tem_duplicados": True,
                "numero_pedido_loja": "260330GDQVHGXX",
                "pedido_atual_eh_canonico": True,
                "pedido_canonico": {"id": 10, "pedido_bling_numero": "11680", "nf_numero": "011100"},
                "pedidos_duplicados": [{"id": 11, "pedido_bling_numero": "11681"}],
                "pedidos_seguro_ids": [11],
                "pedidos_bloqueados_ids": [],
                "bloqueios": [],
                "requer_revisao_manual": False,
            }
        },
    )

    registros = _enriquecer_registros_contexto(
        _FakeDB([]),
        "tenant-1",
        [
            {
                "id": 1,
                "pedido_integrado_id": 10,
                "pedido_bling_id": "25439737683",
                "nf_bling_id": "25443301147",
                "details": {},
            }
        ],
    )

    registro = registros[0]
    assert registro["nf_numero"] == "011100"
    assert registro["duplicidade"]["tem_duplicados"] is True
    assert registro["acoes_disponiveis"]["pode_consolidar_duplicidade"] is True
