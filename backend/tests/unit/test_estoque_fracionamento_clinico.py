from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.estoque import fracionamento_clinico as service
from app.produtos_models import (
    EstoqueFracionamentoConversao,
    EstoqueFracionamentoVinculo,
    EstoqueMovimentacao,
    Produto,
    ProdutoLote,
)


class _FakeQuery:
    def __init__(self, items):
        self.items = items

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def with_for_update(self):
        return self

    def all(self):
        return list(self.items)

    def first(self):
        return self.items[0] if self.items else None


class _FakeDb:
    def __init__(self, mapping):
        self.mapping = mapping
        self.added = []
        self.committed = False
        self._next_id = 100

    def query(self, model):
        return _FakeQuery(self.mapping.get(model, []))

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = self._next_id
            self._next_id += 1
        self.added.append(obj)

    def flush(self):
        return None

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        return None


def _produto(produto_id, nome, unidade, estoque, custo):
    return SimpleNamespace(
        id=produto_id,
        codigo=f"P-{produto_id}",
        nome=nome,
        unidade=unidade,
        estoque_atual=estoque,
        preco_custo=custo,
        ativo=True,
        situacao=True,
        controlar_estoque=True,
        controle_lote=False,
        tipo_produto="SIMPLES",
        tipo_kit=None,
        is_parent=False,
    )


def test_fracionamento_baixa_frasco_e_cria_saldo_clinico(monkeypatch):
    monkeypatch.setattr(
        "app.bling_estoque_sync.sincronizar_bling_background", lambda *args: None
    )
    origem = _produto(10, "Dipirona 20 ml", "UN", 4, 30)
    destino = _produto(11, "Dipirona uso clinico", "ML", 0, 0)
    db = _FakeDb(
        {
            Produto: [origem, destino],
            EstoqueFracionamentoVinculo: [],
            ProdutoLote: [],
        }
    )
    payload = SimpleNamespace(
        produto_origem_id=10,
        produto_destino_id=11,
        quantidade_origem=1,
        fator_conversao=20,
        validade_apos_abertura_dias=28,
        lote_origem_id=None,
        documento="CONSULTA-42",
        observacao="Abertura para atendimento",
    )

    resultado = service.executar_fracionamento_clinico(
        db,
        tenant_id="tenant-a",
        current_user=SimpleNamespace(id=7),
        payload=payload,
    )

    assert db.committed is True
    assert origem.estoque_atual == 3
    assert destino.estoque_atual == 20
    assert resultado["quantidade_destino"] == 20
    assert resultado["custo_destino_unitario"] == 1.5
    assert destino.controle_lote is True

    conversao = next(
        item for item in db.added if isinstance(item, EstoqueFracionamentoConversao)
    )
    movimentos = [item for item in db.added if isinstance(item, EstoqueMovimentacao)]
    lote_clinico = next(item for item in db.added if isinstance(item, ProdutoLote))
    assert conversao.validade_apos_abertura_em is not None
    assert lote_clinico.quantidade_disponivel == 20
    assert [item.tipo for item in movimentos] == ["saida", "entrada"]
    assert all(item.referencia_id == conversao.id for item in movimentos)
    assert all(item.referencia_tipo == "fracionamento_clinico" for item in movimentos)


def test_sugestao_abre_apenas_as_embalagens_necessarias():
    origem = _produto(10, "Dipirona 20 ml", "UN", 4, 30)
    destino = _produto(11, "Dipirona uso clinico", "ML", 1, 1.5)
    vinculo = SimpleNamespace(
        id=8,
        produto_origem=origem,
        fator_conversao=20,
        validade_apos_abertura_dias=28,
    )
    db = _FakeDb({Produto: [destino], EstoqueFracionamentoVinculo: [vinculo]})

    resultado = service.sugerir_fracionamento_clinico(
        db,
        tenant_id="tenant-a",
        produto_destino_id=11,
        quantidade_necessaria=22,
    )

    assert resultado["necessita_fracionamento"] is True
    assert resultado["deficit"] == 21
    assert resultado["sugestao"]["quantidade_origem"] == 2
    assert resultado["sugestao"]["quantidade_destino"] == 40


def test_fracionamento_rejeita_meia_embalagem():
    origem = _produto(10, "Dipirona 20 ml", "UN", 4, 30)
    destino = _produto(11, "Dipirona uso clinico", "ML", 0, 0)
    db = _FakeDb({Produto: [origem, destino]})
    payload = SimpleNamespace(
        produto_origem_id=10,
        produto_destino_id=11,
        quantidade_origem=0.5,
        fator_conversao=20,
    )

    with pytest.raises(HTTPException) as exc:
        service.executar_fracionamento_clinico(
            db,
            tenant_id="tenant-a",
            current_user=SimpleNamespace(id=7),
            payload=payload,
        )

    assert exc.value.status_code == 422
    assert "quantidade inteira" in exc.value.detail


def test_fracionamento_exige_regularizacao_de_saldo_clinico_sem_lote():
    origem = _produto(10, "Dipirona 20 ml", "UN", 4, 30)
    destino = _produto(11, "Dipirona uso clinico", "ML", 5, 1.5)
    db = _FakeDb({Produto: [origem, destino], ProdutoLote: []})
    payload = SimpleNamespace(
        produto_origem_id=10,
        produto_destino_id=11,
        quantidade_origem=1,
        fator_conversao=20,
    )

    with pytest.raises(HTTPException) as exc:
        service.executar_fracionamento_clinico(
            db,
            tenant_id="tenant-a",
            current_user=SimpleNamespace(id=7),
            payload=payload,
        )

    assert exc.value.status_code == 409
    assert "saldo sem lote valido" in exc.value.detail
