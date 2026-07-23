import importlib
from types import SimpleNamespace

from tests.route_contract_helpers import method_routes


def _orcamentos():
    return importlib.import_module("app.veterinario_orcamentos")


def _router_routes() -> set[tuple[str, str]]:
    from app.veterinario_routes import router

    return set(method_routes(router))


def test_monta_item_de_catalogo_com_custo_preco_e_margem_estimados():
    orcamentos = _orcamentos()
    catalogo = SimpleNamespace(
        id=7,
        nome="Consulta com medicacao",
        descricao="Atendimento clinico",
        categoria="consulta",
        valor_padrao=150,
        insumos=[
            {"produto_id": 11, "quantidade": 2, "baixar_estoque": True},
            {"produto_id": 12, "quantidade": 0.5, "baixar_estoque": True},
        ],
    )
    produtos = {
        11: SimpleNamespace(
            id=11, nome="Seringa", unidade="un", preco_custo=4, preco_venda=10
        ),
        12: SimpleNamespace(
            id=12, nome="Medicamento", unidade="ml", preco_custo=20, preco_venda=35
        ),
    }

    item = orcamentos.montar_item_orcamento_catalogo(catalogo, produtos, quantidade=2)

    assert item["origem"] == "catalogo"
    assert item["catalogo_id"] == 7
    assert item["nome"] == "Consulta com medicacao"
    assert item["quantidade"] == 2
    assert item["custo_unitario_estimado"] == 18
    assert item["preco_unitario_sugerido"] == 150
    assert item["preco_unitario"] == 150
    assert item["custo_total_estimado"] == 36
    assert item["preco_total"] == 300
    assert item["margem_valor"] == 264
    assert item["margem_percentual"] == 88
    assert item["insumos"][0]["custo_total"] == 8


def test_monta_item_de_produto_usa_custo_e_preco_de_venda_sem_baixar_estoque():
    orcamentos = _orcamentos()
    produto = SimpleNamespace(
        id=44,
        nome="Defenza 2 - 4,5kg",
        unidade="un",
        preco_custo=62.25,
        preco_venda=99.9,
        estoque_atual=3,
    )

    item = orcamentos.montar_item_orcamento_produto(produto, quantidade=3)

    assert item["origem"] == "produto"
    assert item["produto_id"] == 44
    assert item["nome"] == "Defenza 2 - 4,5kg"
    assert item["quantidade"] == 3
    assert item["custo_unitario_estimado"] == 62.25
    assert item["preco_unitario_sugerido"] == 99.9
    assert item["preco_unitario"] == 99.9
    assert item["custo_total_estimado"] == 186.75
    assert item["preco_total"] == 299.7
    assert item["margem_valor"] == 112.95
    assert item["baixar_estoque"] is False


def test_calcula_totais_do_orcamento_a_partir_dos_itens():
    orcamentos = _orcamentos()

    totais = orcamentos.calcular_totais_orcamento(
        [
            {"custo_total_estimado": 36, "preco_total": 300},
            {"custo_total_estimado": 186.75, "preco_total": 299.7},
        ]
    )

    assert totais == {
        "custo_total_estimado": 222.75,
        "preco_total": 599.7,
        "margem_valor": 376.95,
        "margem_percentual": 62.86,
    }


def test_rotas_de_orcamento_veterinario_estao_registradas():
    routes = _router_routes()

    assert ("/vet/orcamentos", "GET") in routes
    assert ("/vet/orcamentos", "POST") in routes
    assert ("/vet/orcamentos/{orcamento_id}", "GET") in routes
    assert ("/vet/orcamentos/{orcamento_id}", "PATCH") in routes
