from contextlib import nullcontext
from decimal import Decimal
from types import SimpleNamespace

import pytest
import requests

from app.bling_integration import BlingAPI, _montar_url_bling, prevalidar_fiscal_venda
from app import bling_integration_fiscal
from app.bling_integration_parts import core as bling_core


class _FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f"{self.status_code} Error", response=self
            )

    def json(self):
        return self._payload


def _make_api():
    api = BlingAPI.__new__(BlingAPI)
    api.base_url = "https://api.bling.com.br/Api/v3"
    api.access_token = "token-antigo"
    api.enable_jwt = "1"
    api.ambiente = "producao"
    return api


def _make_venda_nfce():
    produto = SimpleNamespace(
        id=10,
        codigo="DEFENZA-TESTE",
        codigo_barras="7890000000000",
        nome="Defenza teste",
        unidade="UN",
        ncm="30049099",
        origem="0",
        cfop="5102",
    )
    item = SimpleNamespace(
        id=20,
        produto=produto,
        preco_unitario=100,
        desconto_item=0,
        quantidade=1,
    )
    return SimpleNamespace(
        id=30,
        tenant_id="tenant-1",
        itens=[item],
        cliente=None,
        desconto_valor=0,
        taxa_entrega=0,
        tem_entrega=False,
        data_venda=None,
    )


def test_configuracao_jwt_nao_pode_ser_desativada_por_variavel(monkeypatch):
    monkeypatch.setattr(bling_core, "ENV_PATHS", [])
    monkeypatch.setenv("BLING_ENABLE_JWT", "0")

    runtime_config = bling_core._load_bling_runtime_config()

    assert runtime_config["enable_jwt"] == "1"


def test_prevalidacao_sugere_ncm_para_racao_caes_gatos_com_ncm_zerado():
    produto = SimpleNamespace(
        id=10,
        codigo="SACHE-TESTE",
        codigo_barras="7890000000000",
        nome="Sache Gran Plus Gourmet Gato Adulto Trato Urinario Frango 85g",
        unidade="UN",
        ncm="00000000",
        origem="0",
        cfop="5102",
    )
    venda = SimpleNamespace(
        id=30,
        tenant_id="tenant-1",
        itens=[
            SimpleNamespace(
                id=20,
                produto=produto,
                preco_unitario=1.99,
                desconto_item=0,
                quantidade=1,
            )
        ],
        cliente=None,
    )

    validacao = prevalidar_fiscal_venda(venda, "nfce")

    assert validacao["bloqueios"] == []
    assert validacao["correcoes"][0]["campo"] == "ncm"
    assert validacao["correcoes"][0]["valor_atual"] == "00000000"
    assert validacao["correcoes"][0]["valor_sugerido"] == "23091000"
    assert validacao["correcoes"][0]["confianca"] == "baixa"
    assert validacao["correcoes"][0]["preenchimento_automatico"] is False
    assert validacao["pode_emitir"] is False


def test_ncm_com_um_unico_exemplo_em_categoria_generica_tem_baixa_confianca():
    class Query:
        def join(self, *_args):
            return self

        def filter(self, *_args):
            return self

        def limit(self, *_args):
            return self

        def all(self):
            return [("23091000",)]

    class Db:
        def query(self, *_args):
            return Query()

    produto = SimpleNamespace(
        id=28128,
        categoria_id=298,
        departamento_id=None,
        categoria=SimpleNamespace(nome="GRUPO DIVERSOS"),
        departamento=None,
    )

    sugestao = bling_integration_fiscal._sugerir_ncm_por_historico(
        Db(), "tenant-1", produto
    )

    assert sugestao["valor"] == "23091000"
    assert sugestao["confianca"] == "baixa"
    assert sugestao["preenchimento_automatico"] is False
    assert "1 de 1" in sugestao["motivo"]


def test_prevalidacao_direta_identifica_campos_editaveis_e_sugestoes(monkeypatch):
    venda = _make_venda_nfce()
    monkeypatch.setattr(
        bling_integration_fiscal,
        "_resolver_fiscal_item_nfe",
        lambda *_args: {
            "ncm": "39269090",
            "origem_mercadoria": "0",
            "cfop": "5102",
            "cst_icms": None,
            "pis_cst": None,
            "cofins_cst": None,
        },
    )
    monkeypatch.setattr(
        bling_integration_fiscal,
        "_melhor_sugestao_catalogo",
        lambda *_args: {
            "categoria_fiscal": "Acessorios",
            "cst_icms": "102",
            "pis_cst": "49",
            "cofins_cst": "49",
            "observacao": "Sugestao baseada no catalogo fiscal.",
        },
    )

    validacao = bling_integration_fiscal.prevalidar_produtos_fiscais_venda(
        venda, exigir_documento_completo=True
    )

    assert validacao["bloqueios"] == []
    assert {item["campo"] for item in validacao["correcoes"]} == {
        "cst_icms",
        "pis_cst",
        "cofins_cst",
    }
    assert all(item["produto_id"] == 10 for item in validacao["correcoes"])
    assert all(
        item["codigo_barras"] == "7890000000000" for item in validacao["correcoes"]
    )


def test_prevalidacao_oferece_opcoes_do_simples_com_baixa_confianca(monkeypatch):
    venda = _make_venda_nfce()
    monkeypatch.setattr(
        bling_integration_fiscal,
        "_resolver_fiscal_item_nfe",
        lambda *_args: {
            "ncm": "39269090",
            "origem_mercadoria": "0",
            "cfop": "5102",
            "cst_icms": None,
            "pis_cst": None,
            "cofins_cst": None,
            "icms_st": False,
        },
    )
    monkeypatch.setattr(
        bling_integration_fiscal,
        "_config_fiscal_empresa",
        lambda *_args: SimpleNamespace(
            regime_tributario="Simples Nacional",
            simples_ativo=True,
            pis_cst_padrao=None,
            cofins_cst_padrao=None,
        ),
    )
    monkeypatch.setattr(
        bling_integration_fiscal, "_melhor_sugestao_catalogo", lambda *_args: None
    )

    validacao = bling_integration_fiscal.prevalidar_produtos_fiscais_venda(
        venda, object(), exigir_documento_completo=True
    )

    sugestoes = {item["campo"]: item for item in validacao["correcoes"]}
    assert sugestoes["cst_icms"]["valor_sugerido"] == "102"
    assert sugestoes["pis_cst"]["valor_sugerido"] == "49"
    assert sugestoes["cofins_cst"]["valor_sugerido"] == "49"
    assert all(item["confianca"] == "baixa" for item in sugestoes.values())
    assert all(item["preenchimento_automatico"] is False for item in sugestoes.values())
    assert validacao["contexto_fiscal"] == {
        "regime_tributario": "Simples Nacional",
        "uf": None,
        "simples_nacional": True,
    }


def test_catalogo_opcional_falha_dentro_de_savepoint_sem_interromper_validacao(
    monkeypatch,
):
    eventos = []

    class Savepoint:
        def __enter__(self):
            eventos.append("abriu")

        def __exit__(self, exc_type, _exc, _traceback):
            eventos.append(("fechou", exc_type))
            return False

    class Db:
        def begin_nested(self):
            return Savepoint()

    def catalogo_indisponivel(*_args):
        raise RuntimeError("tabela de catalogo indisponivel")

    monkeypatch.setattr(
        bling_integration_fiscal,
        "sugerir_fiscal_por_descricao",
        catalogo_indisponivel,
    )

    sugestao = bling_integration_fiscal._melhor_sugestao_catalogo(
        Db(), SimpleNamespace(nome="Portao pet")
    )

    assert sugestao is None
    assert eventos == ["abriu", ("fechou", RuntimeError)]


def test_emissao_fiscal_pelo_bling_permanece_bloqueada(monkeypatch):
    api = _make_api()
    venda = _make_venda_nfce()

    chamadas_bling = []

    def fake_request(*args, **kwargs):
        chamadas_bling.append((args, kwargs))
        return {"data": {"id": 123}}

    monkeypatch.setattr(api, "_request", fake_request)

    with pytest.raises(RuntimeError, match="IntNFe"):
        api.emitir_nota_fiscal(venda, "nfce")

    assert chamadas_bling == []


def test_request_renova_token_e_repete_quando_bling_retorna_invalid_token(monkeypatch):
    api = _make_api()
    chamadas = []

    def fake_get(url, headers=None, params=None, timeout=None):
        chamadas.append(
            {
                "url": url,
                "authorization": headers.get("Authorization"),
                "params": params,
                "timeout": timeout,
            }
        )
        if len(chamadas) == 1:
            return _FakeResponse(
                401,
                {
                    "error": {
                        "type": "invalid_token",
                        "message": "invalid_token",
                        "description": "The access token provided is invalid or expired",
                    }
                },
            )
        return _FakeResponse(200, {"data": [{"id": 123}]})

    def fake_renovar():
        api.access_token = "token-novo"
        return True

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr(api, "_renovar_token_automatico", fake_renovar)

    resposta = api._request("GET", "/nfe", data={"dataInicial": "2026-03-30"})

    assert resposta == {"data": [{"id": 123}]}
    assert len(chamadas) == 2
    assert chamadas[0]["authorization"] == "Bearer token-antigo"
    assert chamadas[1]["authorization"] == "Bearer token-novo"
    assert chamadas[0]["timeout"] == 30


def test_request_reaproveita_token_renovado_por_outro_processo(monkeypatch):
    api = _make_api()
    chamadas = []
    recargas = 0
    renovacoes = []

    def fake_get(url, headers=None, params=None, timeout=None):
        chamadas.append(headers.get("Authorization"))
        if len(chamadas) == 1:
            return _FakeResponse(
                401,
                {"error": {"type": "invalid_token", "message": "invalid_token"}},
            )
        return _FakeResponse(200, {"data": []})

    def fake_recarregar():
        nonlocal recargas
        recargas += 1
        if recargas == 2:
            api.access_token = "token-do-outro-processo"
            api.refresh_token = "refresh-do-outro-processo"
            return True
        return False

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr(api, "_recarregar_tokens_compartilhados", fake_recarregar)
    monkeypatch.setattr(
        api, "_renovar_token_automatico", lambda: renovacoes.append(True)
    )

    assert api._request("GET", "/nfe") == {"data": []}
    assert chamadas == ["Bearer token-antigo", "Bearer token-do-outro-processo"]
    assert renovacoes == []


def test_request_nao_renova_para_erro_diferente_de_invalid_token(monkeypatch):
    api = _make_api()
    renovacoes = []

    def fake_get(url, headers=None, params=None, timeout=None):
        return _FakeResponse(
            429,
            {
                "error": {
                    "type": "too_many_requests",
                    "message": "rate_limit",
                }
            },
        )

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr(
        api, "_renovar_token_automatico", lambda: renovacoes.append(True)
    )

    try:
        api._request("GET", "/nfe")
        assert False, "Era esperado erro para 429"
    except Exception as exc:
        assert "429" in str(exc)

    assert renovacoes == []


def test_montar_url_bling_exige_endpoint_relativo_seguro():
    assert (
        _montar_url_bling("https://api.bling.com.br/Api/v3/", "/nfe/123")
        == "https://api.bling.com.br/Api/v3/nfe/123"
    )

    for endpoint in ("https://evil.test/nfe", "nfe/123", "/../nfe", "/nfe\\123"):
        with pytest.raises(ValueError, match="Endpoint Bling invalido"):
            _montar_url_bling("https://api.bling.com.br/Api/v3", endpoint)


def test_baixar_danfe_usa_timeout(monkeypatch):
    api = _make_api()
    chamadas = []

    class FakeResponse:
        content = b"%PDF"

        def raise_for_status(self):
            return None

    def fake_get(url, headers=None, timeout=None):
        chamadas.append({"url": url, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("requests.get", fake_get)

    assert api.baixar_danfe(123) == b"%PDF"
    assert chamadas == [
        {
            "url": "https://api.bling.com.br/Api/v3/nfe/123/danfe",
            "headers": api._get_headers(),
            "timeout": 30,
        }
    ]


def test_renovar_access_token_usa_timeout(monkeypatch):
    api = _make_api()
    api.enable_jwt = "0"
    api.client_id = "client-id"
    api.client_secret = "client-secret"
    api.refresh_token = "refresh-token"
    chamadas = []

    class FakeResponse:
        status_code = 200
        text = "ok"

        def json(self):
            return {
                "access_token": "token-novo",
                "refresh_token": "refresh-novo",
                "expires_in": 21600,
            }

    def fake_post(url, headers=None, data=None, timeout=None):
        chamadas.append(
            {"url": url, "headers": headers, "data": data, "timeout": timeout}
        )
        return FakeResponse()

    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setattr(
        "app.bling_oauth_routes._salvar_tokens",
        lambda *_args, **_kwargs: None,
    )

    assert api.renovar_access_token()["access_token"] == "token-novo"
    assert chamadas[0]["url"] == "https://api.bling.com.br/Api/v3/oauth/token"
    assert chamadas[0]["data"] == {
        "grant_type": "refresh_token",
        "refresh_token": "refresh-token",
    }
    assert chamadas[0]["headers"]["enable-jwt"] == "1"
    assert chamadas[0]["timeout"] == 30


def test_renovar_access_token_prefere_refresh_mais_recente_do_arquivo(monkeypatch):
    api = _make_api()
    api.client_id = "client-id-antigo"
    api.client_secret = "client-secret-antigo"
    api.refresh_token = "refresh-antigo"
    chamadas = []

    class FakeResponse:
        status_code = 200
        text = "ok"

        def json(self):
            return {
                "access_token": "token-novo",
                "refresh_token": "refresh-novo",
                "expires_in": 21600,
            }

    def fake_post(url, headers=None, data=None, timeout=None):
        chamadas.append({"url": url, "data": data})
        return FakeResponse()

    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setattr(
        "app.bling_integration_parts.core._bling_token_lock", nullcontext
    )
    monkeypatch.setattr(
        "app.bling_integration_parts.core._load_bling_runtime_config",
        lambda **_kwargs: {
            "access_token": "token-compartilhado",
            "refresh_token": "refresh-compartilhado",
            "client_id": "client-id-atual",
            "client_secret": "client-secret-atual",
        },
    )
    monkeypatch.setattr(
        "app.bling_oauth_routes._salvar_tokens",
        lambda *_args, **_kwargs: None,
    )

    api.renovar_access_token()

    assert chamadas[0]["url"] == "https://api.bling.com.br/Api/v3/oauth/token"
    assert chamadas[0]["data"]["refresh_token"] == "refresh-compartilhado"


def test_renovar_access_token_propaga_falha_ao_persistir(monkeypatch):
    api = _make_api()
    api.client_id = "client-id"
    api.client_secret = "client-secret"
    api.refresh_token = "refresh-token"

    class FakeResponse:
        status_code = 200
        text = "ok"

        def json(self):
            return {
                "access_token": "token-novo",
                "refresh_token": "refresh-novo",
                "expires_in": 21600,
            }

    monkeypatch.setattr("requests.post", lambda *_args, **_kwargs: FakeResponse())
    monkeypatch.setattr(
        "app.bling_oauth_routes._salvar_tokens",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("db indisponivel")
        ),
    )

    with pytest.raises(RuntimeError, match="db indisponivel"):
        api.renovar_access_token()


def test_payload_nfce_usa_serie_3_e_deixa_numero_para_sequencia_do_bling():
    api = _make_api()
    payload = api._montar_payload(_make_venda_nfce(), "nfce")

    assert payload["modelo"] == 65
    assert payload["tipo"] == 1
    assert payload["serie"] == 3
    assert payload["numero"] is None


def test_payload_nfce_usa_taxa_entrega_da_venda_sem_campo_legado():
    api = _make_api()
    venda = _make_venda_nfce()
    venda.tem_entrega = True
    venda.taxa_entrega = 12.5

    assert not hasattr(venda, "taxa_entrega_total")

    payload = api._montar_payload(venda, "nfce")

    assert payload["totais"]["valorFrete"] == 12.5
    assert payload["totais"]["valorTotal"] == 112.5
    assert payload["transporte"]["frete"] == 12.5


def test_payload_desconto_rateado_nao_multiplica_nem_desconta_duas_vezes():
    venda = _make_venda_nfce()
    item = venda.itens[0]
    item.quantidade = Decimal("2.000")
    item.preco_unitario = Decimal("179.90")
    item.desconto_item = Decimal("25.00")
    venda.desconto_valor = Decimal("25.00")
    venda.total = Decimal("334.80")

    payload = _make_api()._montar_payload(venda, "nfce")

    assert payload["itens"][0]["valor"] == 179.9
    assert "desconto" not in payload["itens"][0]
    assert payload["desconto"] == 25.0
    assert payload["totais"] == {
        "valorProdutos": 359.8,
        "valorFrete": 0.0,
        "valorDesconto": 25.0,
        "valorTotal": 334.8,
    }


def test_payload_preserva_desconto_global_sem_rateio_e_frete():
    venda = _make_venda_nfce()
    venda.desconto_valor = Decimal("10.00")
    venda.tem_entrega = True
    venda.taxa_entrega = Decimal("12.50")
    venda.total = Decimal("102.50")

    payload = _make_api()._montar_payload(venda, "nfce")

    assert payload["desconto"] == 10.0
    assert payload["transporte"]["frete"] == 12.5
    assert payload["totais"]["valorTotal"] == 102.5


def test_payload_arredonda_cada_item_vendido_por_peso():
    venda = _make_venda_nfce()
    modelo = venda.itens[0]
    venda.itens = [
        SimpleNamespace(
            produto=modelo.produto,
            quantidade=Decimal(q),
            preco_unitario=Decimal(p),
            desconto_item=0,
        )
        for q, p in [("1.097", "9.30"), ("1", "139.90"), ("1", "149.90")]
    ]
    venda.total = Decimal("300.00")

    payload = _make_api()._montar_payload(venda, "nfce")

    assert payload["totais"]["valorProdutos"] == 300.0
    assert payload["totais"]["valorTotal"] == 300.0


def test_payload_envia_campos_fiscais_e_endereco_no_formato_bling():
    venda = _make_venda_nfce()
    venda.itens[0].produto.cest = "2200100"
    venda.cliente = SimpleNamespace(
        nome="Cliente teste",
        cpf="",
        cnpj="",
        email="",
        telefone="",
        endereco="Rua Teste",
        numero="123",
        complemento="",
        bairro="Centro",
        cidade="Presidente Prudente",
        estado="SP",
        cep="19010-000",
    )

    payload = _make_api()._montar_payload(venda, "nfce")

    item = payload["itens"][0]
    assert item["classificacaoFiscal"] == "30049099"
    assert item["cest"] == "2200100"
    assert item["origem"] == 0
    assert "ncm" not in item
    assert payload["contato"]["endereco"]["endereco"] == "Rua Teste"
    assert "logradouro" not in payload["contato"]["endereco"]
