import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.intnfe.delivery_address import DeliveryAddressError, resolver_endereco_entrega


def _customer(**changes):
    values = {
        "endereco": "Rua Sao Joao",
        "numero": "123",
        "complemento": "Casa A",
        "bairro": "Centro",
        "cidade": "Andradina",
        "estado": "SP",
        "codigo_municipio": "3502101",
        "cep": "16900-600",
        "enderecos_adicionais": [],
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _label(address):
    fields = vars(address) if isinstance(address, SimpleNamespace) else address
    complement = f" - {fields['complemento']}" if fields.get("complemento") else ""
    return f"{fields['endereco']}, {fields.get('numero', '')}{complement}, {fields['bairro']}, {fields['cidade']}/{fields['estado']}"


def _sale(customer=None, selected=None):
    customer = customer or _customer()
    return SimpleNamespace(
        cliente=customer,
        endereco_entrega=selected if selected is not None else _label(customer),
    )


def test_principal_selecionado_usa_dados_proprios_sem_alterar_venda():
    sale = _sale()
    original = deepcopy(sale)

    assert resolver_endereco_entrega(sale) == {
        "logradouro": "Rua Sao Joao",
        "numero": "123",
        "complemento": "Casa A",
        "bairro": "Centro",
        "municipio": "Andradina",
        "uf": "SP",
        "codigoMunicipio": "3502101",
        "cep": "16900600",
    }
    assert sale == original


def test_normaliza_acentos_caixa_e_espacos_sem_remover_numero_ou_complemento():
    sale = _sale(selected="  RUA SÃO JOÃO, 123 - CASA A,   CENTRO, ANDRADINA/SP  ")
    assert resolver_endereco_entrega(sale)["numero"] == "123"


@pytest.mark.parametrize("as_json", [False, True])
def test_alternativo_selecionado_nao_herda_cep_ou_ibge_do_principal(as_json):
    alternative = {
        "endereco": "Rua Dois",
        "numero": "90",
        "bairro": "Outra Vila",
        "cidade": "Tres Lagoas",
        "estado": "MS",
        "cep": "79601-970",
        "codigo_municipio": "5008305",
    }
    addresses = json.dumps([alternative]) if as_json else [alternative]
    sale = _sale(_customer(enderecos_adicionais=addresses), _label(alternative))

    result = resolver_endereco_entrega(sale)

    assert result["logradouro"] == "Rua Dois"
    assert result["uf"] == "MS"
    assert result["codigoMunicipio"] == "5008305"
    assert result["cep"] == "79601970"
    assert "complemento" not in result


@pytest.mark.parametrize("field", ["codigo_municipio", "cep"])
def test_alternativo_incompleto_nao_completa_com_dados_do_principal(field):
    alternative = dict(vars(_customer(endereco="Rua Alternativa")))
    alternative[field] = ""
    sale = _sale(_customer(enderecos_adicionais=[alternative]), _label(alternative))

    with pytest.raises(DeliveryAddressError) as error:
        resolver_endereco_entrega(sale)

    api_field = "codigoMunicipio" if field == "codigo_municipio" else field
    assert error.value.field == f"entrega.endereco.{api_field}"


def test_sem_endereco_selecionado_nao_adota_principal_automaticamente():
    with pytest.raises(DeliveryAddressError, match="Selecione"):
        resolver_endereco_entrega(_sale(selected=""))


@pytest.mark.parametrize(
    "selected",
    [
        "Endereco livre sem cadastro",
        "Rua Sao Joao, 999 - Casa A, Centro, Andradina/SP",
        "Rua Sao Joao, 123 - Casa B, Centro, Andradina/SP",
    ],
)
def test_texto_divergente_ou_complemento_diferente_nao_usa_principal(selected):
    with pytest.raises(DeliveryAddressError, match="nao corresponde"):
        resolver_endereco_entrega(_sale(selected=selected))


def test_enderecos_ambiguos_com_cep_diferente_bloqueiam():
    alternative = dict(vars(_customer(cep="16900-601")))
    sale = _sale(_customer(enderecos_adicionais=[alternative]))

    with pytest.raises(DeliveryAddressError, match="dados diferentes"):
        resolver_endereco_entrega(sale)


def test_copias_iguais_do_mesmo_endereco_nao_exigem_revisao_desnecessaria():
    alternative = dict(vars(_customer()))
    sale = _sale(_customer(enderecos_adicionais=[alternative, alternative.copy()]))
    assert resolver_endereco_entrega(sale)["cep"] == "16900600"


def test_copias_com_cep_sem_mascara_acentos_e_caixa_nao_sao_ambiguas():
    alternative = dict(vars(_customer(cep="16900600", endereco="RUA SÃO JOÃO")))
    sale = _sale(_customer(enderecos_adicionais=[alternative]))
    assert resolver_endereco_entrega(sale)["cep"] == "16900600"


def test_endereco_completo_textual_nao_pode_contradizer_campos_estruturados():
    alternative = dict(vars(_customer(endereco="Rua Diferente")))
    alternative["endereco_completo"] = "Rua Livre, 900, Centro, Andradina/SP"
    sale = _sale(
        _customer(enderecos_adicionais=[alternative]), alternative["endereco_completo"]
    )

    with pytest.raises(DeliveryAddressError, match="diverge"):
        resolver_endereco_entrega(sale)


def test_alias_conflitante_nao_pode_se_passar_pelo_principal():
    alternative = dict(vars(_customer(endereco="Rua Diferente")))
    alternative["endereco_completo"] = _label(_customer())
    sale = _sale(_customer(enderecos_adicionais=[alternative]))
    with pytest.raises(DeliveryAddressError, match="dados diferentes"):
        resolver_endereco_entrega(sale)


@pytest.mark.parametrize("number", ["S/N", "sem numero", "123-A", "0"])
def test_numero_textual_informado_e_preservado(number):
    assert (
        resolver_endereco_entrega(_sale(_customer(numero=number)))["numero"] == number
    )


@pytest.mark.parametrize(
    "changes,field",
    [
        ({"cep": ""}, "cep"),
        ({"cep": "16900"}, "cep"),
        ({"codigo_municipio": ""}, "codigoMunicipio"),
        ({"codigo_municipio": "350210"}, "codigoMunicipio"),
        ({"estado": "Sao Paulo"}, "uf"),
        ({"estado": "ZZ"}, "uf"),
        ({"bairro": ""}, "bairro"),
        ({"numero": ""}, "numero"),
    ],
)
def test_endereco_selecionado_exige_campos_completos_do_contrato(changes, field):
    sale = _sale(_customer(**changes))
    with pytest.raises(DeliveryAddressError) as error:
        resolver_endereco_entrega(sale)
    assert error.value.field == f"entrega.endereco.{field}"


def test_json_invalido_nao_impede_principal_selecionado_valido():
    sale = _sale(_customer(enderecos_adicionais="{invalido"))
    assert resolver_endereco_entrega(sale)["logradouro"] == "Rua Sao Joao"
