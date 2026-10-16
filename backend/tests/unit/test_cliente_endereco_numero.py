"""O endereco informado exige numero, preservando textos e PUTs parciais."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.clientes.common import _validar_numero_endereco_cliente
from app.clientes.schemas import ClienteCreate, ClienteUpdate


def _cadastro_atual(**changes):
    fields = {
        "cep": "79601970",
        "endereco": "Estrada rural",
        "numero": "S/N",
        "complemento": None,
        "bairro": "Zona Rural",
        "cidade": "Tres Lagoas",
        "estado": "MS",
        "codigo_municipio": "5008305",
    }
    fields.update(changes)
    return SimpleNamespace(**fields)


def _exigir_rejeicao(dados, atual=None):
    with pytest.raises(HTTPException) as error:
        _validar_numero_endereco_cliente(dados, atual)
    assert error.value.status_code == 422
    assert "numero" in str(error.value.detail).casefold().replace("ú", "u")


@pytest.mark.parametrize("field", ["cep", "endereco", "bairro"])
@pytest.mark.parametrize("numero", [None, "", " \t\n "])
def test_criacao_com_dados_de_endereco_rejeita_numero_vazio(field, numero):
    values = {"cep": "79601970", "endereco": "Estrada rural", "bairro": "Zona Rural"}
    dados = ClienteCreate(nome="Cliente", numero=numero, **{field: values[field]})

    _exigir_rejeicao(dados)


def test_criacao_com_endereco_rejeita_numero_omitido():
    dados = ClienteCreate(nome="Cliente", endereco="Estrada rural")

    _exigir_rejeicao(dados)


@pytest.mark.parametrize(
    "numero",
    ["S/N", "SN", "s/n", "Sem numero", "sem número", "123", "123-A", "0", " S/N "],
)
def test_criacao_aceita_numero_textual_sem_alterar_valor(numero):
    dados = ClienteCreate(nome="Cliente", endereco="Estrada rural", numero=numero)

    _validar_numero_endereco_cliente(dados)

    assert dados.numero == numero


def test_criacao_sem_endereco_nao_exige_numero():
    dados = ClienteCreate(nome="Cliente")

    _validar_numero_endereco_cliente(dados)

    assert dados.numero is None


def test_criacao_com_cidade_uf_ou_complemento_sozinhos_nao_exige_numero():
    dados = ClienteCreate(
        nome="Cliente",
        cidade="Tres Lagoas",
        estado="MS",
        complemento="Referencia",
        codigo_municipio="5008305",
        cep="  ",
        endereco="\t",
        bairro="\n",
    )

    _validar_numero_endereco_cliente(dados)

    assert dados.numero is None


def test_put_parcial_herda_numero_existente_quando_omitido():
    atual = _cadastro_atual()
    dados = ClienteUpdate(complemento="Latitude e longitude")

    _validar_numero_endereco_cliente(dados, atual)

    assert "numero" not in dados.model_fields_set
    assert atual.numero == "S/N"


@pytest.mark.parametrize("numero", [None, "", " \t\n "])
def test_put_com_numero_explicitamente_vazio_nao_herda_numero_antigo(numero):
    dados = ClienteUpdate(numero=numero)

    _exigir_rejeicao(dados, _cadastro_atual())


@pytest.mark.parametrize(
    "changes",
    [
        {"cep": "79601970"},
        {"endereco": "Outra estrada"},
        {"bairro": "Zona Rural"},
        {"complemento": "Referencia"},
        {"cidade": "Tres Lagoas"},
        {"estado": "MS"},
        {"codigo_municipio": "5008305"},
    ],
)
def test_put_que_toca_endereco_legado_incompleto_exige_numero(changes):
    dados = ClienteUpdate(**changes)

    _exigir_rejeicao(dados, _cadastro_atual(numero=None))


@pytest.mark.parametrize(
    "changes", [{"nome": "Novo nome"}, {"telefone": "67999991111"}, {}]
)
def test_put_independente_do_endereco_nao_bloqueia_legado_incompleto(changes):
    atual = _cadastro_atual(numero=None)
    dados = ClienteUpdate(**changes)

    _validar_numero_endereco_cliente(dados, atual)

    assert atual.numero is None


def test_put_preenche_numero_textual_em_endereco_legado():
    atual = _cadastro_atual(numero=None)
    dados = ClienteUpdate(numero="sem número")

    _validar_numero_endereco_cliente(dados, atual)

    assert dados.numero == "sem número"
    assert atual.numero is None


def test_put_adiciona_endereco_a_cadastro_sem_endereco_e_exige_numero():
    atual = _cadastro_atual(cep=None, endereco=None, bairro=None, numero=None)

    _exigir_rejeicao(ClienteUpdate(endereco="Estrada rural"), atual)


def test_put_limpa_todo_endereco_e_pode_limpar_numero():
    fields = {
        field: None
        for field in (
            "cep",
            "endereco",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            "codigo_municipio",
        )
    }
    dados = ClienteUpdate(**fields)
    atual = _cadastro_atual()

    _validar_numero_endereco_cliente(dados, atual)

    assert dados.numero is None
    assert atual.numero == "S/N"


def test_put_cidade_uf_sem_endereco_nao_exige_numero():
    atual = _cadastro_atual(cep=None, endereco=None, bairro=None, numero=None)
    dados = ClienteUpdate(cidade="Tres Lagoas", estado="MS")

    _validar_numero_endereco_cliente(dados, atual)

    assert dados.numero is None
