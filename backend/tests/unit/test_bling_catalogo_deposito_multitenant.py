from __future__ import annotations

import pytest

from app.bling_integration_parts.catalogo import BlingCatalogoMixin


class BlingCatalogoCaptura(BlingCatalogoMixin):
    def __init__(
        self,
        token_source: str,
        *,
        stock_deposit_id: int | None = None,
        depositos: list[dict] | None = None,
    ):
        self.token_source = token_source
        self.stock_deposit_id = stock_deposit_id
        self.tenant_id = "tenant-gabi"
        self.depositos = depositos or []
        self.requisicoes: list[tuple[str, str, dict]] = []

    def _request(self, metodo: str, endpoint: str, data: dict):
        self.requisicoes.append((metodo, endpoint, data))
        if endpoint == "/depositos":
            return {"data": self.depositos}
        return {"data": []}


def test_tenant_descobre_e_persiste_deposito_padrao_sem_herdar_global(monkeypatch):
    persistidos = []
    monkeypatch.setenv("BLING_DEPOSITO_ID", "999")
    monkeypatch.setattr(
        "app.services.bling_connection_service.save_bling_stock_deposit_id",
        lambda **kwargs: persistidos.append(kwargs),
    )
    bling = BlingCatalogoCaptura(
        token_source="tenant",
        depositos=[
            {"id": 12345, "descricao": "Geral", "situacao": 1, "padrao": True},
            {"id": 67890, "descricao": "ML FULL", "situacao": 1, "padrao": False},
        ],
    )

    bling.atualizar_estoque_produto("123", 7)

    assert bling.requisicoes[0][1] == "/depositos"
    metodo, endpoint, payload = bling.requisicoes[1]
    assert (metodo, endpoint) == ("POST", "/estoques")
    assert payload["deposito"] == {"id": 12345}
    assert persistidos == [{"tenant_id": "tenant-gabi", "stock_deposit_id": 12345}]


def test_tenant_consulta_saldo_no_deposito_configurado(monkeypatch):
    monkeypatch.setenv("BLING_DEPOSITO_ID", "999")
    bling = BlingCatalogoCaptura(token_source="tenant", stock_deposit_id=12345)

    bling.consultar_saldo_estoque("123")

    metodo, endpoint, params = bling.requisicoes[0]
    assert (metodo, endpoint) == ("GET", "/estoques/saldos/12345")
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


def test_multiplos_depositos_sem_padrao_exigem_configuracao(monkeypatch):
    monkeypatch.delenv("BLING_DEPOSITO_ID", raising=False)
    bling = BlingCatalogoCaptura(
        token_source="tenant",
        depositos=[
            {"id": 12345, "situacao": 1, "padrao": False},
            {"id": 67890, "situacao": 1, "padrao": False},
        ],
    )

    with pytest.raises(ValueError, match="Nenhum deposito padrao"):
        bling.atualizar_estoque_produto("123", 7)
