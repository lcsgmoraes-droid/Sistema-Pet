from datetime import datetime
from types import SimpleNamespace

from app.services.pendencia_estoque_relatorio import montar_relatorio_lista_espera


def _pendencia(
    pendencia_id,
    *,
    cliente_id,
    cliente_nome,
    produto,
    quantidade,
):
    return SimpleNamespace(
        id=pendencia_id,
        cliente=SimpleNamespace(
            id=cliente_id,
            nome=cliente_nome,
            celular=f"2199999000{cliente_id}",
            telefone=None,
        ),
        produto=produto,
        quantidade_desejada=quantidade,
        status="pendente",
        prioridade=1,
        data_registro=datetime(2026, 8, 27, 10, 30),
    )


def test_relatorio_discrimina_sku_e_agrupa_por_fornecedor_e_marca():
    fornecedor = SimpleNamespace(
        nome_fantasia="Distribuidora Pet",
        razao_social="Distribuidora Pet LTDA",
        nome="Cadastro fornecedor",
    )
    special_dog = SimpleNamespace(
        id=10,
        codigo="SD-CARNE-15KG",
        nome="Special Dog Carne 15 kg",
        marca=SimpleNamespace(nome="Special Dog"),
        fornecedor=fornecedor,
    )
    formula_natural = SimpleNamespace(
        id=20,
        codigo="FN-FRANGO-10KG",
        nome="Formula Natural Frango 10 kg",
        marca=SimpleNamespace(nome="Formula Natural"),
        fornecedor=fornecedor,
    )
    pendencias = [
        _pendencia(
            1,
            cliente_id=100,
            cliente_nome="Ana",
            produto=special_dog,
            quantidade=1,
        ),
        _pendencia(
            2,
            cliente_id=200,
            cliente_nome="Bruno",
            produto=special_dog,
            quantidade=2,
        ),
        _pendencia(
            3,
            cliente_id=100,
            cliente_nome="Ana",
            produto=formula_natural,
            quantidade=1,
        ),
    ]

    relatorio = montar_relatorio_lista_espera(pendencias)

    assert relatorio["resumo"] == {
        "total_registros": 3,
        "total_clientes": 2,
        "total_skus": 2,
        "quantidade_total": 4.0,
    }
    assert relatorio["produtos"][1]["sku"] == "SD-CARNE-15KG"
    assert relatorio["produtos"][1]["total_clientes"] == 2
    assert relatorio["produtos"][1]["quantidade_total"] == 3.0

    grupo = relatorio["agrupado_por_fornecedor"][0]
    assert grupo["fornecedor"] == "Distribuidora Pet"
    assert grupo["total_clientes"] == 2
    assert grupo["total_skus"] == 2
    assert [marca["marca"] for marca in grupo["marcas"]] == [
        "Formula Natural",
        "Special Dog",
    ]
    assert len(relatorio["detalhes"]) == 3


def test_relatorio_mantem_produtos_sem_marca_ou_fornecedor_visiveis():
    produto = SimpleNamespace(
        id=30,
        codigo=None,
        nome="Produto sem classificacao",
        marca=None,
        fornecedor=None,
    )

    relatorio = montar_relatorio_lista_espera(
        [
            _pendencia(
                4,
                cliente_id=300,
                cliente_nome="Carla",
                produto=produto,
                quantidade=1,
            )
        ]
    )

    assert relatorio["produtos"][0]["sku"] == "Sem SKU"
    assert relatorio["produtos"][0]["marca"] == "Sem marca"
    assert relatorio["agrupado_por_fornecedor"][0]["fornecedor"] == "Sem fornecedor"
