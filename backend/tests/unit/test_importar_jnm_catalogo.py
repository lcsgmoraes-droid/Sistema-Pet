"""Regras de conversao para o backup JN Moura, sem dados reais do cliente."""

from copy import deepcopy

from importar_jnm_catalogo import is_generic_name, prepare_rows


def _person(source_id, name):
    return {
        "source_id": str(source_id),
        "nome": name,
        "tipo_pessoa": "F",
        "documento": "",
        "telefone": "",
        "telefone2": "",
        "celular": "",
        "email": "",
        "endereco": "",
        "numero": "",
        "bairro": "",
        "cep": "",
        "cidade": "",
        "uf": "",
        "inativo": "N",
        "data_nascimento": "",
        "data_cadastro": "",
    }


def _product(source_id, name, stock, barcode=""):
    return {
        "source_id": str(source_id),
        "nome": name,
        "grupo_id": "1",
        "grupo_nome": "Racoes",
        "codigo_barras": barcode,
        "preco_venda": "12.50",
        "preco_custo": "8.00",
        "unidade": "UN",
        "inativo": "N",
        "servico": "N",
        "ncm": "",
        "estoque_minimo": "0",
        "estoque_maximo": "0",
        "estoque_raw": stock,
        "data_cadastro": "",
    }


def test_prepare_rows_preserves_roles_and_zeroes_only_negative_stock():
    source = {
        "clientes.csv": [_person(7, "Maria"), _person(8, "Consumidor Final")],
        "fornecedores.csv": [_person(7, "Maria"), _person(9, "Distribuidora")],
        "produtos.csv": [
            _product(1, "VARIADOS", "-100"),
            _product(2, "Racao A", "-2", "7891234567890"),
            _product(3, "Racao B", "3.5", "7891234567890"),
            _product(4, "Cores variadas", "1"),
        ],
    }

    clients, products, metrics = prepare_rows(deepcopy(source))

    assert [(c["codigo"], c["tipo_cadastro"]) for c in clients] == [
        ("7", "cliente"),
        ("F-7", "fornecedor"),
        ("F-9", "fornecedor"),
    ]
    assert [p["codigo"] for p in products] == ["2", "3", "4"]
    assert [str(p["estoque_atual"]) for p in products] == ["0", "3.5", "1"]
    assert [p["codigo_barras"] for p in products] == [None, None, None]
    assert metrics["clientes_genericos_excluidos"] == 1
    assert metrics["produtos_genericos_excluidos"] == 1
    assert metrics["estoques_negativos_zerados"] == 1
    assert metrics["codigos_barras_duplicados_limpos"] == 2
    assert metrics["saldo_estoque_importavel"] == "4.5"


def test_generic_names_require_exact_match():
    assert is_generic_name("  diversós ")
    assert not is_generic_name("Brinquedos diversos")
