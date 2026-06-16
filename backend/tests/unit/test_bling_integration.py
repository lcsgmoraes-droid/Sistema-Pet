import requests
import pytest
from types import SimpleNamespace

from app.bling_integration import BlingAPI, prevalidar_fiscal_venda


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
    assert validacao["pode_emitir"] is False


def test_emitir_nfce_bloqueia_ncm_zerado_antes_de_criar_nota_no_bling(monkeypatch):
    api = _make_api()
    venda = _make_venda_nfce()
    venda.itens[0].produto.ncm = "00000000"

    chamadas_bling = []

    def fake_request(*args, **kwargs):
        chamadas_bling.append((args, kwargs))
        return {"data": {"id": 123}}

    monkeypatch.setattr(api, "_request", fake_request)

    with pytest.raises(ValueError, match="NCM"):
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
