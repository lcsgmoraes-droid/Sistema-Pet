import os
from datetime import datetime
from types import SimpleNamespace

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app import produtos_routes as routes  # noqa: E402


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, rows):
        self.rows = rows

    def query(self, *args):
        return FakeQuery(self.rows)


def test_mapa_validade_proxima_produtos_usa_primeira_validade_por_produto():
    primeira_validade = datetime(2026, 6, 10)
    validade_mais_distante = datetime(2026, 9, 10)
    rows = [
        (10, "LOTE-A", primeira_validade),
        (10, "LOTE-B", validade_mais_distante),
        (11, "LOTE-C", validade_mais_distante),
    ]

    resultado = routes._mapa_validade_proxima_produtos(
        FakeDb(rows),
        [SimpleNamespace(id=10), SimpleNamespace(id=11)],
        ["tenant-1"],
    )

    assert resultado[10] == {
        "validade_proxima_listagem": primeira_validade,
        "lote_validade_proxima": "LOTE-A",
    }
    assert resultado[11] == {
        "validade_proxima_listagem": validade_mais_distante,
        "lote_validade_proxima": "LOTE-C",
    }


def test_enriquecer_produto_listagem_expoe_validade_calculada():
    produto = SimpleNamespace(
        id=10,
        tenant_id="tenant-1",
        categoria=None,
        tipo_produto="SIMPLES",
        tipo_kit=None,
        estoque_atual=5,
        preco_venda=20,
        preco_promocional=None,
        promocao_inicio=None,
        promocao_fim=None,
    )
    validade = datetime(2026, 6, 10)

    routes._enriquecer_produto_listagem(
        FakeDb([]),
        produto,
        "tenant-1",
        reservas_por_produto={},
        incluir_detalhes_composto=False,
        validade_por_produto={
            10: {
                "validade_proxima_listagem": validade,
                "lote_validade_proxima": "LOTE-A",
            }
        },
    )

    assert produto.validade_proxima_listagem == validade
    assert produto.lote_validade_proxima == "LOTE-A"


def test_enriquecer_produto_listagem_nao_atribui_property_validade_proxima():
    class ProdutoComProperty(SimpleNamespace):
        @property
        def validade_proxima(self):
            return None

    produto = ProdutoComProperty(
        id=10,
        tenant_id="tenant-1",
        categoria=None,
        tipo_produto="SIMPLES",
        tipo_kit=None,
        estoque_atual=5,
        preco_venda=20,
        preco_promocional=None,
        promocao_inicio=None,
        promocao_fim=None,
    )
    validade = datetime(2026, 6, 10)

    routes._enriquecer_produto_listagem(
        FakeDb([]),
        produto,
        "tenant-1",
        reservas_por_produto={},
        incluir_detalhes_composto=False,
        validade_por_produto={
            10: {
                "validade_proxima_listagem": validade,
                "lote_validade_proxima": "LOTE-A",
            }
        },
    )

    assert produto.validade_proxima is None
    assert produto.validade_proxima_listagem == validade
