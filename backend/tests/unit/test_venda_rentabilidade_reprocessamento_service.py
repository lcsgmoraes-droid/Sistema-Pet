from datetime import datetime
from types import SimpleNamespace

import pytest

from app import dre_plano_contas_models  # noqa: F401
from app.produtos_models import EstoqueMovimentacao
from app.services import venda_rentabilidade_reprocessamento_service as service
from app.vendas_models import Venda


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def options(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return list(self._rows)


class _FakeDb:
    def __init__(self, vendas, movimentos):
        self.vendas = vendas
        self.movimentos = movimentos

    def query(self, model):
        if model is Venda:
            return _FakeQuery(self.vendas)
        if model is EstoqueMovimentacao:
            return _FakeQuery(self.movimentos)
        return _FakeQuery([])


def test_reprocessamento_usa_custo_atual_e_corrige_movimentacao(monkeypatch):
    tenant_id = "tenant-reprocessamento"
    produto = SimpleNamespace(id=10, nome="Produto com custo corrigido", preco_custo=12.5)
    venda = SimpleNamespace(
        id=100,
        tenant_id=tenant_id,
        numero_venda="REPROC-0001",
        data_venda=datetime(2026, 6, 10, 14, 30),
        subtotal=60.0,
        desconto_valor=0.0,
        total=60.0,
        status="finalizada",
        canal="loja_fisica",
        pagamentos=[],
        itens=[
            SimpleNamespace(
                produto_id=produto.id,
                produto=produto,
                quantidade=2,
                preco_unitario=30,
            )
        ],
        rentabilidade_snapshot={
            "snapshot_version": 5,
            "custo_produtos": 10,
            "lucro": 50,
        },
    )
    movimento = SimpleNamespace(
        tenant_id=tenant_id,
        produto_id=produto.id,
        produto=produto,
        tipo="saida",
        motivo="venda",
        quantidade=-2,
        custo_unitario=5,
        valor_total=10,
        referencia_tipo="venda",
        referencia_id=venda.id,
        status="confirmado",
    )

    def fake_get_or_build(venda_arg, _db, tenant_arg, **kwargs):
        assert venda_arg is venda
        assert tenant_arg == tenant_id
        assert kwargs["force_refresh"] is True
        assert kwargs["persist_if_missing"] is True
        assert kwargs["estoque_custos_por_produto"] == {
            produto.id: {"quantidade": 2.0, "valor_total": 25.0}
        }
        snapshot = {
            "custo_produtos": 25.0,
            "lucro": 35.0,
            "itens": [{"custo_unitario": 12.5}],
        }
        venda_arg.rentabilidade_snapshot = snapshot
        return snapshot

    monkeypatch.setattr(service, "get_or_build_venda_rentabilidade_snapshot", fake_get_or_build)

    resultado = service.reprocessar_rentabilidade_vendas(
        _FakeDb(vendas=[venda], movimentos=[movimento]),
        tenant_id=tenant_id,
        venda_ids=[venda.id],
    )

    assert resultado["total_reprocessado"] == 1
    assert movimento.custo_unitario == pytest.approx(12.5)
    assert movimento.valor_total == pytest.approx(25)
    assert venda.rentabilidade_snapshot["custo_produtos"] == pytest.approx(25)
    assert venda.rentabilidade_snapshot["lucro"] == pytest.approx(35)
    assert venda.rentabilidade_snapshot["itens"][0]["custo_unitario"] == pytest.approx(12.5)
