from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

from scripts import reconciliar_reservas_bling as script


TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")


class _FakeDB:
    def __init__(self):
        self.commit_calls = 0
        self.rollback_calls = 0
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1


def test_parse_preservar_saldos_aceita_virgula_decimal():
    assert script._parse_preservar_saldos(["ATC517=24", "ABC=1,5"]) == {
        "ATC517": 24.0,
        "ABC": 1.5,
    }


def test_parse_preservar_saldos_rejeita_valor_sem_sku():
    with pytest.raises(ValueError, match="Use SKU=SALDO"):
        script._parse_preservar_saldos(["24"])


def test_consulta_bling_classifica_nf_independente_da_situacao(monkeypatch):
    respostas = {
        "BL-1": {
            "situacao": {"id": 24},
            "resumo_nf": {"id": "NF-1", "situacao_codigo": 5},
        },
        "BL-2": {"situacao": {"id": 12}, "resumo_nf": None},
        "BL-3": {"situacao": {"id": 9}, "resumo_nf": None},
    }

    def consultar(pedido_bling_id):
        if pedido_bling_id == "BL-4":
            raise RuntimeError("falha simulada")
        return respostas[pedido_bling_id]

    monkeypatch.setattr(script, "_consultar_pedido_bling", consultar)
    monkeypatch.setattr(
        script,
        "_resumir_ultima_nf_do_pedido_bling",
        lambda pedido: pedido.get("resumo_nf"),
    )

    snapshots = script._consultar_referencias_no_bling(
        [
            {"pedido_id": 1, "pedido_bling_id": "BL-1"},
            {"pedido_id": 2, "pedido_bling_id": "BL-2"},
            {"pedido_id": 3, "pedido_bling_id": "BL-3"},
            {"pedido_id": 4, "pedido_bling_id": "BL-4"},
        ]
    )

    assert [snapshot["classificacao"] for snapshot in snapshots] == [
        "nf_autorizada",
        "cancelado",
        "atendido_sem_nf",
        "erro",
    ]


def test_snapshot_cancelado_sem_saida_libera_reserva(monkeypatch):
    pedido = SimpleNamespace(
        id=12,
        tenant_id=TENANT_ID,
        payload={},
        status="confirmado",
        cancelado_em=None,
    )
    item = SimpleNamespace(liberado_em=None, vendido_em=None)

    class FakeQuery:
        def __init__(self, alvo):
            self.alvo = alvo

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            if self.alvo is script.PedidoIntegrado:
                return pedido
            return None

        def all(self):
            if self.alvo is script.PedidoIntegradoItem:
                return [item]
            return []

    class FakeDB:
        def __init__(self):
            self.commit_calls = 0

        def query(self, alvo):
            return FakeQuery(alvo)

        def add(self, obj):
            return None

        def commit(self):
            self.commit_calls += 1

    db = FakeDB()
    monkeypatch.setattr(
        script,
        "_montar_payload_pedido",
        lambda **kwargs: {"pedido": kwargs["pedido_completo"]},
    )

    acao = script._aplicar_snapshot_bling(
        db,
        snapshot={
            "pedido_id": 12,
            "pedido_remoto": {"id": "BL-12"},
            "resumo_nf": None,
            "classificacao": "cancelado",
        },
        aplicar=True,
    )

    assert acao == "cancelado_sem_saida_reserva_liberada"
    assert pedido.status == "cancelado"
    assert pedido.cancelado_em is not None
    assert item.liberado_em is not None
    assert db.commit_calls == 1


def test_planejamento_preserva_saldo_explicito_e_balanco_posterior(monkeypatch):
    criado_em = datetime.utcnow() - timedelta(days=1)
    pedido = SimpleNamespace(
        id=10,
        tenant_id=TENANT_ID,
        payload={},
        criado_em=criado_em,
    )
    itens = [
        SimpleNamespace(sku="EXPLICITO", quantidade=2),
        SimpleNamespace(sku="BALANCO", quantidade=3),
        SimpleNamespace(sku="SEM_BALANCO", quantidade=4),
    ]
    produtos = {
        "EXPLICITO": SimpleNamespace(id=1),
        "BALANCO": SimpleNamespace(id=2),
        "SEM_BALANCO": SimpleNamespace(id=3),
    }

    monkeypatch.setattr(
        script,
        "_ultima_nf",
        lambda payload: {"id": "NF-1", "numero": "123"},
    )
    monkeypatch.setattr(
        script,
        "_movimentos_nf_pedido",
        lambda *args, **kwargs: ({}, {}),
    )
    monkeypatch.setattr(
        script,
        "_alvos_fisicos_item",
        lambda db, **kwargs: (
            produtos[kwargs["item"].sku],
            [
                {
                    "produto": produtos[kwargs["item"].sku],
                    "quantidade": kwargs["item"].quantidade,
                }
            ],
        ),
    )

    plano = script._planejar_pedido(
        object(),
        pedido=pedido,
        itens=itens,
        ultimos_balancos={2: criado_em + timedelta(hours=1)},
        produtos_preservados={
            1: {
                "sku": "EXPLICITO",
                "saldo_esperado": 24,
                "produto": produtos["EXPLICITO"],
            }
        },
        cache_componentes={},
        cache_produtos={},
    )

    assert [acao["acao"] for acao in plano["acoes"]] == [
        "documentar_por_balanco",
        "documentar_por_balanco",
        "baixar_estoque",
    ]
    assert plano["acoes"][0]["preservacao_explicita"] is True
    assert plano["acoes"][1]["preservacao_explicita"] is False


def test_aplicacao_faz_um_commit_atomico_por_pedido(monkeypatch):
    db = _FakeDB()
    produto = SimpleNamespace(id=1, estoque_atual=24)
    item = SimpleNamespace(vendido_em=None)
    pedido = SimpleNamespace(
        id=10,
        status="confirmado",
        confirmado_em=None,
        pedido_bling_id="BL-10",
        pedido_bling_numero="10",
    )
    plano = {
        "pedido": pedido,
        "itens": [item],
        "nf_bling_id": "NF-10",
        "nf_numero": "100",
        "acoes": [],
        "erros": [],
    }

    monkeypatch.setattr(
        script,
        "_obter_usuario_padrao_tenant",
        lambda **kwargs: SimpleNamespace(id=7),
    )
    monkeypatch.setattr(script, "registrar_evento", lambda **kwargs: None)
    monkeypatch.setattr(
        script,
        "resolver_incidentes_relacionados",
        lambda *args, **kwargs: 0,
    )

    resultado = script._aplicar_planos(
        db,
        planos=[plano],
        tenant_id=TENANT_ID,
        produtos_preservados={
            1: {
                "sku": "ATC517",
                "saldo_esperado": 24,
                "produto": produto,
            }
        },
    )

    assert resultado == {
        "pedidos_aplicados": 1,
        "pedidos_com_erro": 0,
        "erros": [],
    }
    assert db.commit_calls == 1
    assert db.rollback_calls == 0
    assert item.vendido_em is not None
    assert pedido.confirmado_em is not None


def test_aplicacao_reverte_pedido_se_saldo_preservado_mudaria(monkeypatch):
    db = _FakeDB()
    produto = SimpleNamespace(id=1, estoque_atual=24)
    item = SimpleNamespace(vendido_em=None)
    pedido = SimpleNamespace(
        id=11,
        status="confirmado",
        confirmado_em=None,
        pedido_bling_id="BL-11",
        pedido_bling_numero="11",
    )
    plano = {
        "pedido": pedido,
        "itens": [item],
        "nf_bling_id": "NF-11",
        "nf_numero": "101",
        "acoes": [
            {
                "acao": "baixar_estoque",
                "produto": produto,
                "quantidade": 1,
            }
        ],
        "erros": [],
    }

    monkeypatch.setattr(
        script,
        "_obter_usuario_padrao_tenant",
        lambda **kwargs: SimpleNamespace(id=7),
    )
    monkeypatch.setattr(
        script,
        "_baixar_produto_fisico",
        lambda *args, **kwargs: setattr(produto, "estoque_atual", 23),
    )
    monkeypatch.setattr(script, "registrar_evento", lambda **kwargs: None)
    monkeypatch.setattr(
        script,
        "resolver_incidentes_relacionados",
        lambda *args, **kwargs: 0,
    )

    resultado = script._aplicar_planos(
        db,
        planos=[plano],
        tenant_id=TENANT_ID,
        produtos_preservados={
            1: {
                "sku": "ATC517",
                "saldo_esperado": 24,
                "produto": produto,
            }
        },
    )

    assert resultado["pedidos_aplicados"] == 0
    assert resultado["pedidos_com_erro"] == 1
    assert "Saldo preservado de ATC517 mudaria" in resultado["erros"][0]["erro"]
    assert db.commit_calls == 0
    assert db.rollback_calls == 1
