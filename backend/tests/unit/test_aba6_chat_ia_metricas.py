from datetime import datetime
from types import SimpleNamespace

import pytest

from app.financeiro_models import ContaPagar
from app.ia.aba6_chat_ia_parts.metricas import ChatIAMetricasMixin


class _FakeLoad:
    def selectinload(self, *_args, **_kwargs):
        return self


@pytest.fixture(autouse=True)
def _ignorar_loader_options_no_banco_falso(monkeypatch):
    monkeypatch.setattr(
        "sqlalchemy.orm.selectinload", lambda *_args, **_kwargs: _FakeLoad()
    )


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.apenas_dre_operacional = False

    def options(self, *_args, **_kwargs):
        return self

    def filter(self, *conditions):
        texto = " ".join(str(condition).lower() for condition in conditions)
        if "contas_pagar.nota_entrada_id is null" in texto:
            self.apenas_dre_operacional = True
        if "contas_pagar.afeta_dre is true" in texto:
            self.apenas_dre_operacional = True
        return self

    def all(self):
        if self.apenas_dre_operacional:
            return [
                row
                for row in self.rows
                if getattr(row, "nota_entrada_id", None) is None
                and getattr(row, "afeta_dre", True) is True
            ]
        return list(self.rows)


class _FakeDb:
    def __init__(self, vendas, contas):
        self.vendas = vendas
        self.contas = contas

    def query(self, model):
        if model is ContaPagar:
            return _FakeQuery(self.contas)
        return _FakeQuery(self.vendas)


class _Metricas(ChatIAMetricasMixin):
    def __init__(self, db):
        self.db = db


def test_dre_simplificada_ignora_compra_de_estoque_das_notas():
    venda = SimpleNamespace(
        subtotal=1000,
        taxa_entrega=0,
        desconto_valor=0,
        total=1000,
        itens=[
            SimpleNamespace(
                quantidade=2,
                produto=SimpleNamespace(preco_custo=200),
            )
        ],
    )
    despesa_operacional = SimpleNamespace(
        valor_original=100,
        nota_entrada_id=None,
        afeta_dre=True,
    )
    compra_estoque_nf = SimpleNamespace(
        valor_original=900,
        nota_entrada_id=10,
        afeta_dre=False,
    )
    service = _Metricas(_FakeDb([venda], [despesa_operacional, compra_estoque_nf]))

    dre = service._obter_dre_simplificada_mes(
        "tenant-1",
        datetime(2026, 6, 1),
        datetime(2026, 6, 30, 23, 59, 59),
    )

    assert dre["receita_liquida"] == 1000
    assert dre["cmv_estimado"] == 400
    assert dre["despesas_operacionais"] == 100
    assert dre["lucro_liquido_estimado"] == 500


def test_ranking_clientes_soma_compras_e_ordena_por_valor():
    cliente_a = SimpleNamespace(nome="Cliente A", nome_fantasia=None, razao_social=None)
    cliente_b = SimpleNamespace(nome="Cliente B", nome_fantasia=None, razao_social=None)
    vendas = [
        SimpleNamespace(
            canal="loja_fisica",
            total=100,
            cliente_id=1,
            cliente=cliente_a,
            itens=[],
        ),
        SimpleNamespace(
            canal="loja_fisica",
            total=250,
            cliente_id=2,
            cliente=cliente_b,
            itens=[],
        ),
        SimpleNamespace(
            canal="site",
            total=200,
            cliente_id=1,
            cliente=cliente_a,
            itens=[],
        ),
    ]
    service = _Metricas(_FakeDb(vendas, []))

    ranking = service._obter_rankings_periodo(
        "tenant-1",
        datetime(2026, 8, 1),
        datetime(2026, 8, 31, 23, 59, 59),
        limite=10,
    )

    assert ranking["top_clientes"] == [
        {
            "cliente_id": 1,
            "cliente": "Cliente A",
            "valor_total": 300.0,
            "quantidade_compras": 2,
        },
        {
            "cliente_id": 2,
            "cliente": "Cliente B",
            "valor_total": 250.0,
            "quantidade_compras": 1,
        },
    ]
