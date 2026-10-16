from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.campaigns import models as _campaign_models  # noqa: F401 - registra FKs do teste
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.cadastro_routes import router
from app.produtos import cadastro_routes
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
from app.security import permissions_decorator


TENANT = UUID("44e1e23b-782a-4466-8a27-5d38a8925021")


@pytest.fixture
def cadastro(db_session, monkeypatch, tenant_context):
    tenant_context(TENANT)
    app = FastAPI()
    app.include_router(router, prefix="/produtos")
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=1),
        TENANT,
    )
    monkeypatch.setattr(
        permissions_decorator, "check_permission", lambda *_args, **_kw: None
    )
    with TestClient(app) as client:
        yield client, db_session


def criar(client, **campos):
    return client.post(
        "/produtos/",
        json={
            "codigo": "TESTE-ENTRADA",
            "nome": "Produto novo",
            "preco_venda": 20,
            "preco_custo": 8,
            **campos,
        },
    )


def test_cadastro_erp_salva_entrada_lote_e_datas_juntos(cadastro):
    client, db = cadastro
    resposta = criar(
        client,
        entrada_inicial={
            "quantidade": 7.5,
            "numero_lote": "FAB-01",
            "data_fabricacao": "2026-10-01",
            "data_validade": "2027-10-01",
        },
    )
    assert resposta.status_code == 201, resposta.text
    produto = db.execute(select(Produto.__table__)).mappings().one()
    lote = db.execute(select(ProdutoLote.__table__)).mappings().one()
    movimento = db.execute(select(EstoqueMovimentacao.__table__)).mappings().one()
    assert produto["estoque_atual"] == 7.5
    assert lote["nome_lote"] == "FAB-01"
    assert lote["quantidade_disponivel"] == 7.5
    assert lote["data_fabricacao"].date().isoformat() == "2026-10-01"
    assert lote["data_validade"].date().isoformat() == "2027-10-01"
    assert movimento["lote_id"] == lote["id"]
    assert movimento["quantidade"] == 7.5


def test_erp_sem_dados_de_lote_registra_somente_saldo_e_movimento(cadastro):
    client, db = cadastro
    resposta = criar(client, entrada_inicial={"quantidade": 3})
    assert resposta.status_code == 201, resposta.text
    assert db.execute(select(Produto.__table__)).mappings().one()["estoque_atual"] == 3
    assert db.execute(select(ProdutoLote.__table__)).first() is None
    assert (
        db.execute(select(EstoqueMovimentacao.__table__)).mappings().one()["quantidade"]
        == 3
    )


@pytest.mark.parametrize(
    "entrada",
    [
        {"quantidade": 0, "numero_lote": "L-1"},
        {
            "quantidade": 1,
            "data_fabricacao": "2028-01-01",
            "data_validade": "2027-01-01",
        },
    ],
)
def test_erp_rejeita_entrada_invalida_sem_criar_produto(cadastro, entrada):
    client, db = cadastro
    assert criar(client, entrada_inicial=entrada).status_code == 422
    assert db.execute(select(Produto.__table__)).first() is None


def test_produto_pai_nao_recebe_entrada_inicial(cadastro):
    client, db = cadastro
    resposta = criar(
        client, tipo_produto="PAI", preco_venda=0, entrada_inicial={"quantidade": 2}
    )
    assert resposta.status_code == 400
    assert db.execute(select(Produto.__table__)).first() is None


def test_falha_na_entrada_desfaz_o_cadastro_erp(cadastro, monkeypatch):
    client, db = cadastro

    def falhar_entrada(*_args, **_kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(cadastro_routes, "registrar_entrada_inicial", falhar_entrada)
    resposta = criar(client, entrada_inicial={"quantidade": 4})
    assert resposta.status_code == 500
    assert db.execute(select(Produto.__table__)).first() is None
    assert db.execute(select(ProdutoLote.__table__)).first() is None
    assert db.execute(select(EstoqueMovimentacao.__table__)).first() is None
