import requests

from app.bling_integration import BlingAPI


class _FakeResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} Error", response=self)

    def json(self):
        return self._payload


def _make_api():
    api = BlingAPI.__new__(BlingAPI)
    api.base_url = "https://api.bling.com.br/Api/v3"
    api.access_token = "token-antigo"
    api.enable_jwt = "1"
    return api


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
    monkeypatch.setattr(api, "_renovar_token_automatico", lambda: renovacoes.append(True))

    try:
        api._request("GET", "/nfe")
        assert False, "Era esperado erro para 429"
    except Exception as exc:
        assert "429" in str(exc)

    assert renovacoes == []
