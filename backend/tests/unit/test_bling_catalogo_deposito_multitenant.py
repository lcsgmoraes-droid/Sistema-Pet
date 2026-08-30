from __future__ import annotations

from app.bling_integration_parts.catalogo import BlingCatalogoMixin


class BlingCatalogoCaptura(BlingCatalogoMixin):
    def __init__(self, token_source: str):
        self.token_source = token_source
        self.requisicoes: list[tuple[str, str, dict]] = []

    def _request(self, metodo: str, endpoint: str, data: dict):
        self.requisicoes.append((metodo, endpoint, data))
        return {"data": []}


def test_tenant_nao_herda_deposito_global_ao_atualizar_estoque(monkeypatch):
    monkeypatch.setenv("BLING_DEPOSITO_ID", "999")
    bling = BlingCatalogoCaptura(token_source="tenant")

    bling.atualizar_estoque_produto("123", 7)

    metodo, endpoint, payload = bling.requisicoes[0]
    assert (metodo, endpoint) == ("POST", "/estoques")
    assert "deposito" not in payload


def test_tenant_nao_herda_deposito_global_ao_consultar_saldo(monkeypatch):
    monkeypatch.setenv("BLING_DEPOSITO_ID", "999")
    bling = BlingCatalogoCaptura(token_source="tenant")

    bling.consultar_saldo_estoque("123")

    metodo, endpoint, params = bling.requisicoes[0]
    assert (metodo, endpoint) == ("GET", "/estoques/saldos")
    assert params == {"idsProdutos[]": "123"}


def test_conexao_legada_preserva_deposito_global(monkeypatch):
    monkeypatch.setenv("BLING_DEPOSITO_ID", "999")
    bling = BlingCatalogoCaptura(token_source="legacy")

    bling.atualizar_estoque_produto("123", 7)
    bling.consultar_saldo_estoque("123")

    assert bling.requisicoes[0][2]["deposito"] == {"id": 999}
    assert bling.requisicoes[1][1] == "/estoques/saldos/999"


def test_deposito_explicito_tem_prioridade_em_conexao_tenant(monkeypatch):
    monkeypatch.setenv("BLING_DEPOSITO_ID", "999")
    bling = BlingCatalogoCaptura(token_source="tenant")

    bling.atualizar_estoque_produto("123", 7, deposito_id=321)
    bling.consultar_saldo_estoque("123", deposito_id=321)

    assert bling.requisicoes[0][2]["deposito"] == {"id": 321}
    assert bling.requisicoes[1][1] == "/estoques/saldos/321"
