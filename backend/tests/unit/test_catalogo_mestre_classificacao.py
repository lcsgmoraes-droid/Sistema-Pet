import pytest

from app.services.catalogo_mestre_core import classify_product


@pytest.mark.parametrize(
    ("name", "category", "department"),
    [
        ("Almofada Paris Furacaopet N1", "Acessórios", "Acessórios e Brinquedos"),
        (
            "Aplicador de Remedio/comprimido com ponta de Silicone",
            "Acessórios",
            "Acessórios e Brinquedos",
        ),
        (
            "Bandeja para Granulado e Areia para Gatos",
            "Acessórios",
            "Acessórios e Brinquedos",
        ),
        ("Banheira Gato Classic Furacao Pet", "Acessórios", "Acessórios e Brinquedos"),
        ("Brinquedo Bola porta Petisco", "Brinquedos", "Acessórios e Brinquedos"),
        ("Canister Redondo Para Ração 15 Kg", "Acessórios", "Acessórios e Brinquedos"),
        ("Mordedor Vinil Biscoito", "Brinquedos", "Acessórios e Brinquedos"),
        ("Pa Dosadora para Racao", "Acessórios", "Acessórios e Brinquedos"),
        (
            "Alcon Labcon Club Revitalizante 15ml",
            "Aves>>Ração Aves",
            "Acessórios e Brinquedos",
        ),
        ("Areia decorativa para aquário", "Acessórios", "Acessórios e Brinquedos"),
    ],
)
def test_classificacao_exclui_acessorios_reais_da_origem(name, category, department):
    assert classify_product({"nome": name}, category, department) == "outro"


@pytest.mark.parametrize(
    ("name", "category", "department", "expected"),
    [
        (
            "Racao Premier Racas Especificas Bulldog Adulto 12kg",
            "Acessórios",
            "Acessórios e Brinquedos",
            "racao",
        ),
        ("Royal Canin Adulto 10kg", "Rações", "Alimentação", "racao"),
        (
            "Areia Pipicat Premium Carvao Ativado 4kg",
            "Acessórios",
            "Acessórios e Brinquedos",
            "areia_sanitaria",
        ),
        (
            "Granulado de Madeira para Gato Carepet 10kg",
            "Higiene e Beleza",
            "Higiene e Beleza",
            "areia_sanitaria",
        ),
        ("Totoya Snack Eggy", "Acessórios", "Acessórios e Brinquedos", "petisco"),
        (
            "Petisco Funny Cat Bolas de Pelos Frango 50g",
            "Biscoitos e Petiscos",
            "Alimentação",
            "petisco",
        ),
        ("Coleira Scalibor Grande 65cm", "Farmácia", "Saúde e Farmácia", "medicamento"),
    ],
)
def test_classificacao_preserva_produtos_alvo_mesmo_com_categoria_imperfeita(
    name, category, department, expected
):
    assert classify_product({"nome": name}, category, department) == expected


def test_classificacao_nao_encontra_racao_dentro_da_marca_furacaopet():
    assert (
        classify_product(
            {"nome": "Pote FuracaoPet 500ml"},
            "Acessórios",
            "Acessórios e Brinquedos",
        )
        == "outro"
    )
