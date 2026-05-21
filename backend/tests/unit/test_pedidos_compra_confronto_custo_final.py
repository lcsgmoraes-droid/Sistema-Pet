import os
from types import SimpleNamespace

import pytest

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app import notas_entrada_routes  # noqa: E402
from app import pedidos_compra_routes as routes  # noqa: E402


class _FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return SimpleNamespace(
            nome="Racao Grandfood",
            codigo="GF-001",
            codigo_barras="7891000000010",
        )


class _FakeDb:
    def query(self, *args, **kwargs):
        return _FakeQuery()


def _pedido_com_item(preco_unitario=12.0):
    return SimpleNamespace(
        itens=[
            SimpleNamespace(
                id=10,
                produto_id=1,
                quantidade_pedida=10.0,
                preco_unitario=preco_unitario,
                desconto_item=0.0,
            )
        ],
        valor_frete=0.0,
        valor_desconto=0.0,
    )


def _nota_com_item(valor_unitario=10.0, valor_total=100.0):
    item = SimpleNamespace(
        id=101,
        nota_entrada_id=201,
        produto_id=1,
        quantidade=10.0,
        valor_unitario=valor_unitario,
        valor_total=valor_total,
        descricao="Racao Grandfood",
        codigo_produto="GF-001",
        ean="7891000000010",
    )
    nota = SimpleNamespace(
        id=201,
        itens=[item],
        valor_frete=20.0,
        valor_desconto=0.0,
        numero_nota="123",
        serie="1",
        chave_acesso="abc",
        fornecedor_nome="Grandfood",
        data_emissao=None,
        valor_total=120.0,
    )
    return nota


def _aplicar_composicao_custo_final(monkeypatch):
    def _composicao(_nota):
        return {
            101: {
                "custo_aquisicao_total": 120.0,
                "custo_aquisicao_unitario": 12.0,
            }
        }

    monkeypatch.setattr(notas_entrada_routes, "calcular_composicao_custos_nota", _composicao)


def _assert_custo_final_nf(item, confronto):
    assert item["preco_nf"] == pytest.approx(12.0)
    assert item["valor_nf"] == pytest.approx(120.0)
    assert confronto["resumo"]["total_nf"] == pytest.approx(120.0)


def test_confronto_usa_custo_final_da_nf_no_item_vinculado(monkeypatch):
    _aplicar_composicao_custo_final(monkeypatch)

    confronto = routes._realizar_confronto(
        _pedido_com_item(),
        _nota_com_item(),
        _FakeDb(),
        tenant_id=1,
    )

    item = confronto["itens"][0]
    _assert_custo_final_nf(item, confronto)
    assert item["dif_preco_unit"] == pytest.approx(0.0)
    assert item["status"] == "ok"


def test_confronto_usa_custo_final_da_nf_em_item_nao_pedido(monkeypatch):
    _aplicar_composicao_custo_final(monkeypatch)

    pedido = SimpleNamespace(itens=[], valor_frete=0.0, valor_desconto=0.0)
    confronto = routes._realizar_confronto(
        pedido,
        _nota_com_item(),
        _FakeDb(),
        tenant_id=1,
    )

    item = confronto["itens"][0]
    _assert_custo_final_nf(item, confronto)
    assert item["dif_valor"] == pytest.approx(120.0)
    assert item["status"] == "nao_pedido"
