from types import SimpleNamespace

from app.produtos.valorizacao import (
    departamento_id_produto,
    fornecedor_nome_produto,
    nome_area_produto,
    resolver_metricas_valorizacao_produto,
)


def test_nome_area_produto_prefere_departamento_direto():
    produto = SimpleNamespace(
        departamento=SimpleNamespace(nome="Loja"),
        categoria=SimpleNamespace(departamento=SimpleNamespace(nome="Categoria")),
    )

    assert nome_area_produto(produto) == "Loja"


def test_nome_area_produto_usa_departamento_da_categoria_como_fallback():
    produto = SimpleNamespace(
        departamento=None,
        categoria=SimpleNamespace(departamento=SimpleNamespace(nome="Banho")),
    )

    assert nome_area_produto(produto) == "Banho"


def test_departamento_id_produto_usa_categoria_quando_nao_tem_departamento_direto():
    produto = SimpleNamespace(
        departamento_id=None,
        categoria=SimpleNamespace(departamento_id=42),
    )

    assert departamento_id_produto(produto) == 42


def test_fornecedor_nome_produto_prefere_vinculo_principal_ativo():
    fornecedor_principal = SimpleNamespace(nome="Fornecedor principal")
    fornecedor_secundario = SimpleNamespace(nome="Fornecedor secundario")
    produto = SimpleNamespace(
        fornecedor=None,
        fornecedores_alternativos=[
            SimpleNamespace(ativo=True, e_principal=False, fornecedor=fornecedor_secundario),
            SimpleNamespace(ativo=True, e_principal=True, fornecedor=fornecedor_principal),
        ],
    )

    assert fornecedor_nome_produto(produto) == "Fornecedor principal"


def test_resolver_metricas_valorizacao_produto_simples_desconta_reservas():
    produto = SimpleNamespace(
        id=10,
        estoque_atual=8,
        preco_custo=4.5,
        preco_venda=9,
        tipo_produto="SIMPLES",
        tipo_kit=None,
    )

    metricas = resolver_metricas_valorizacao_produto(
        db=object(),
        produto=produto,
        reservas_por_produto={10: 2},
    )

    assert metricas == {
        "estoque_atual": 8.0,
        "estoque_reservado": 2.0,
        "estoque_disponivel": 6.0,
        "preco_custo": 4.5,
        "preco_venda": 9.0,
        "valor_custo_total": 36.0,
        "valor_venda_total": 72.0,
    }


def test_resolver_metricas_valorizacao_produto_kit_virtual_usa_servicos_injetados():
    class KitEstoqueFake:
        @staticmethod
        def calcular_estoque_virtual_kit(db, produto_id, tenant_id=None, reservas_por_produto=None):
            assert produto_id == 99
            assert tenant_id == "tenant-1"
            assert reservas_por_produto == {99: 3}
            return 12

    class KitCustoFake:
        @staticmethod
        def calcular_custo_kit(produto_id, db):
            assert produto_id == 99
            return 7.5

    produto = SimpleNamespace(
        id=99,
        tenant_id="tenant-1",
        estoque_atual=-1,
        preco_custo=1,
        preco_venda=20,
        tipo_produto="VARIACAO",
        tipo_kit="VIRTUAL",
    )

    metricas = resolver_metricas_valorizacao_produto(
        db=object(),
        produto=produto,
        reservas_por_produto={99: 3},
        kit_estoque_service=KitEstoqueFake,
        kit_custo_service=KitCustoFake,
    )

    assert metricas["estoque_atual"] == 12.0
    assert metricas["estoque_reservado"] == 0.0
    assert metricas["estoque_disponivel"] == 12.0
    assert metricas["preco_custo"] == 7.5
    assert metricas["valor_custo_total"] == 90.0
