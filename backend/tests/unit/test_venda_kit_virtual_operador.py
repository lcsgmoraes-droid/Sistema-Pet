from types import SimpleNamespace
from unittest.mock import MagicMock

from app.produtos_models import Produto, ProdutoKitComponente
from app.vendas import estoque_baixa


def test_kit_virtual_baixa_componente_cadastrado_por_outro_usuario(monkeypatch):
    tenant_id = "11111111-1111-1111-1111-111111111111"
    kit = SimpleNamespace(
        id=100,
        nome="Kit com 24 unidades",
        controlar_estoque=True,
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
    )
    componente = SimpleNamespace(produto_componente_id=200, quantidade=24)
    produto_componente = SimpleNamespace(
        id=200,
        nome="Unidade avulsa",
        user_id=48,
        tenant_id=tenant_id,
        tipo_produto="SIMPLES",
        situacao=True,
    )
    query_componentes = MagicMock()
    query_componentes.filter.return_value.all.return_value = [componente]
    query_produto = MagicMock()
    query_produto.filter.return_value.first.return_value = produto_componente
    db = MagicMock()
    db.query.side_effect = lambda model: (
        query_componentes if model is ProdutoKitComponente else query_produto
    )
    baixas = []

    def baixar_estoque(**kwargs):
        baixas.append(kwargs)
        return {
            "produto_nome": produto_componente.nome,
            "estoque_anterior": 948,
            "estoque_novo": 924,
        }

    monkeypatch.setattr(estoque_baixa.EstoqueService, "baixar_estoque", baixar_estoque)

    resultado = estoque_baixa.processar_baixa_estoque_item(
        produto=kit,
        quantidade_vendida=1,
        venda_id=300,
        user_id=60,
        tenant_id=tenant_id,
        db=db,
    )

    filtros_produto = query_produto.filter.call_args.args
    assert any(
        "produtos.tenant_id" in str(filtro) and filtro.right.value == tenant_id
        for filtro in filtros_produto
    )
    assert not any("produtos.user_id" in str(filtro) for filtro in filtros_produto)
    assert resultado[0]["produto_id"] == 200
    assert baixas[0]["quantidade"] == 24
    assert baixas[0]["user_id"] == 60
