"""Preferência de endereço no PDV, somente na empresa fictícia da homologação local."""

from urllib.parse import urlparse
from uuid import uuid4

import pytest

from tests import test_plano_basico_e2e as jornada_basica

api = jornada_basica.api
e2e_config = jornada_basica.e2e_config
pytestmark = pytest.mark.e2e_long
FLAG = "mostrar_endereco_cliente_pdv"


@pytest.fixture(scope="module", autouse=True)
def somente_local_antes_da_autenticacao(e2e_config):
    assert urlparse(e2e_config.base_url).hostname in {"localhost", "127.0.0.1"}


def _get(api, path, **params):
    return api.expect("GET", path, {200}, path, params=params).json()


def test_endereco_na_busca_e_preferencia_persistida_sem_alterar_outras_regras(api):
    identidade = _get(api, "/auth/me-multitenant")
    assert identidade["tenant"]["name"] == "CorePet Homologacao Local"
    assert api.config.tenant_id == "fcbaa106-3b50-4b75-876a-614d157aa670"
    original = _get(api, "/empresa/config/")
    if original["id"] == 0:
        assert original[FLAG] is False
        assert _get(api, "/empresa/config/pdv")[FLAG] is False
        defaults = {key: value for key, value in original.items() if key != "id"}
        criada = api.expect(
            "POST",
            "/empresa/config/",
            {200, 201},
            "endereco_pdv.persistir_defaults_da_homologacao",
            json={},
        ).json()
        assert criada["id"] > 0
        assert {key: value for key, value in criada.items() if key != "id"} == defaults
        original = _get(api, "/empresa/config/")
        assert original == criada
    assert original["id"] > 0
    assert isinstance(original[FLAG], bool)
    outras_regras = {key: value for key, value in original.items() if key != FLAG}
    prefix = "E2E-ENDERECO-PDV-" + uuid4().hex[:12]
    endereco = {
        "cep": "16900-000",
        "endereco": "Rua Fictícia de Homologação",
        "numero": "123",
        "complemento": "Casa A",
        "bairro": "Centro",
        "cidade": "Andradina",
        "estado": "SP",
    }
    clientes = []
    for suffix, dados_endereco in (("-COM", endereco), ("-SEM", {})):
        cliente = api.expect(
            "POST",
            "/clientes/",
            {200, 201},
            "endereco_pdv.cliente_ficticio",
            json={
                "nome": prefix + suffix,
                "tipo_cadastro": "cliente",
                "tipo_pessoa": "PF",
                "telefone": "119" + f"{uuid4().int % 100000000:08d}",
                "observacoes": "Cadastro fictício para aceite local de endereço no PDV.",
                **dados_endereco,
            },
        ).json()
        clientes.append(cliente)

    try:
        for enabled in (False, True, False):
            atualizada = api.expect(
                "PUT",
                "/empresa/config/",
                {200},
                "endereco_pdv.alternar_preferencia",
                json={FLAG: enabled},
            ).json()
            assert atualizada[FLAG] is enabled
            persistida = _get(api, "/empresa/config/")
            assert persistida[FLAG] is enabled
            assert {
                key: value for key, value in persistida.items() if key != FLAG
            } == outras_regras
            pdv = _get(api, "/empresa/config/pdv")
            assert pdv[FLAG] is enabled
            assert (
                pdv["vendedor_obrigatorio_pdv"] == original["vendedor_obrigatorio_pdv"]
            )
            encontrados = _get(api, "/clientes/", search=prefix, limit=20)["items"]
            assert {c["id"] for c in encontrados} == {c["id"] for c in clientes}
            com_endereco = next(c for c in encontrados if c["id"] == clientes[0]["id"])
            sem_endereco = next(c for c in encontrados if c["id"] == clientes[1]["id"])
            assert com_endereco["cep"] == "".join(
                digito for digito in endereco["cep"] if digito.isdigit()
            )
            assert {key: com_endereco[key] for key in endereco if key != "cep"} == {
                key: value for key, value in endereco.items() if key != "cep"
            }
            assert com_endereco["telefone"] == clientes[0]["telefone"]
            assert not sem_endereco["endereco"]
    finally:
        api.expect(
            "PUT",
            "/empresa/config/",
            {200},
            "endereco_pdv.restaurar_preferencia",
            json={FLAG: original[FLAG]},
        )
        restaurada = _get(api, "/empresa/config/")
        assert restaurada == original, (
            "A configuração inicial deve permanecer integralmente igual."
        )
        assert _get(api, "/empresa/config/pdv")[FLAG] is original[FLAG]

    print(
        f"ENDERECO_PDV clientes={clientes[0]['id']},{clientes[1]['id']} "
        f"busca={prefix} flag=false,true,false restaurada={original[FLAG]} "
        "endereco_principal_e_telefone_preservados outras_regras_inalteradas"
    )
