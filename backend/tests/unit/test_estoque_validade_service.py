import os
import re
from datetime import datetime, timezone
from types import SimpleNamespace

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

import pytest

from app.estoque.service import EstoqueService
from app.estoque_validade_service import EstoqueValidadeService
from app.estoque_validade_models import EstoqueValidadeBloqueio


def test_validade_bloqueio_model_declares_statuses_and_quantities():
    campos = EstoqueValidadeBloqueio.__table__.columns

    assert "produto_id" in campos
    assert "lote_id" in campos
    assert "status" in campos
    assert "quantidade_bloqueada" in campos
    assert "quantidade_resolvida" in campos
    assert "custo_total_estimado" in campos
    assert "movimentacao_bloqueio_id" in campos
    assert "movimentacao_resolucao_id" in campos


class FakeDb:
    def __init__(self):
        self.added = []
        self.flushed = 0

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushed += 1
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                obj.id = index


def _produto(estoque=10):
    return SimpleNamespace(
        id=10, nome="Racao Teste", estoque_atual=float(estoque), preco_custo=8.5
    )


def _lote(validade, quantidade=3, status="ativo"):
    return SimpleNamespace(
        id=77,
        produto_id=10,
        nome_lote="L-VAL-1",
        data_validade=validade,
        quantidade_disponivel=float(quantidade),
        custo_unitario=7.0,
        status=status,
    )


def test_bloquear_lote_reduz_vendavel_e_marca_lote_como_bloqueado(monkeypatch):
    monkeypatch.setattr(
        EstoqueService,
        "_resolver_user_id_operacao",
        staticmethod(lambda **kwargs: kwargs["user_id"]),
    )
    db = FakeDb()
    produto = _produto(estoque=10)
    lote = _lote(datetime(2026, 6, 5, tzinfo=timezone.utc), quantidade=3)

    bloqueio = EstoqueValidadeService.bloquear_lote(
        db=db,
        tenant_id="tenant-1",
        user_id=5,
        produto=produto,
        lote=lote,
        agora=datetime(2026, 5, 21, tzinfo=timezone.utc),
        origem="teste",
    )

    assert produto.estoque_atual == pytest.approx(7)
    assert lote.status == "bloqueado_validade"
    assert bloqueio.status == "pendente"
    assert bloqueio.quantidade_bloqueada == pytest.approx(3)
    assert bloqueio.custo_total_estimado == pytest.approx(21)


def test_descartar_bloqueio_nao_reduz_vendavel_duas_vezes(monkeypatch):
    monkeypatch.setattr(
        EstoqueService,
        "_resolver_user_id_operacao",
        staticmethod(lambda **kwargs: kwargs["user_id"]),
    )
    db = FakeDb()
    produto = _produto(estoque=7)
    lote = _lote(
        datetime(2026, 6, 5, tzinfo=timezone.utc),
        quantidade=3,
        status="bloqueado_validade",
    )
    bloqueio = SimpleNamespace(
        id=99,
        produto=produto,
        lote=lote,
        produto_id=10,
        lote_id=77,
        status="pendente",
        quantidade_bloqueada=3.0,
        quantidade_resolvida=0.0,
        custo_unitario=7.0,
        custo_total_estimado=21.0,
        movimentacao_resolucao_id=None,
        decisao=None,
        decidido_por_user_id=None,
        decidido_em=None,
        observacao=None,
    )

    resolvido = EstoqueValidadeService.descartar_bloqueio(
        db=db,
        tenant_id="tenant-1",
        user_id=5,
        bloqueio=bloqueio,
        observacao="Produto vencido separado fisicamente",
        agora=datetime(2026, 5, 22, tzinfo=timezone.utc),
    )

    assert produto.estoque_atual == pytest.approx(7)
    assert lote.quantidade_disponivel == pytest.approx(0)
    assert lote.status == "descartado"
    assert resolvido.status == "descartado"
    assert resolvido.decisao == "descartado"


def test_fifo_de_lotes_consumiveis_usa_apenas_status_ativo():
    import inspect

    source = inspect.getsource(EstoqueService._consumir_lotes_fifo)

    assert re.search(r"ProdutoLote\.status\s*==\s*['\"]ativo['\"]", source)
