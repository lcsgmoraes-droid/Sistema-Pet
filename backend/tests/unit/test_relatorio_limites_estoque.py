from types import SimpleNamespace
import unicodedata
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.produtos import relatorios_limites_routes as limites
from app.produtos_models import (
    Categoria,
    Departamento,
    Marca,
    Produto,
    ProdutoFornecedor,
)


@pytest.fixture
def relatorio(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with engine.connect() as connection:
        connection.connection.driver_connection.create_function(
            "unaccent",
            1,
            lambda value: "".join(
                char
                for char in unicodedata.normalize("NFD", value or "")
                if not unicodedata.combining(char)
            ),
        )
    for model in (Departamento, Categoria, Marca, Cliente, Produto, ProdutoFornecedor):
        model.__table__.create(engine)
    tenant_id, outro_tenant = uuid4(), uuid4()
    db = Session(engine)
    contador = 0

    def produto(nome, atual=5, minimo=10, maximo=20, **extra):
        nonlocal contador
        contador += 1
        registro = dict(
            id=contador,
            nome=nome,
            codigo=f"SKU-{contador}",
            tenant_id=tenant_id,
            estoque_atual=atual,
            estoque_minimo=minimo,
            estoque_maximo=maximo,
            tipo="produto",
            tipo_produto="SIMPLES",
            ativo=True,
            user_id=1,
        )
        registro.update(extra)
        db.execute(Produto.__table__.insert().values(**registro))
        db.commit()
        return contador

    monkeypatch.setattr(
        limites, "get_all_accessible_tenant_ids", lambda *_: [str(tenant_id)]
    )
    permissoes = []
    monkeypatch.setattr(
        "app.security.permissions_decorator.check_permission",
        lambda *a, **k: permissoes.append(a[2]),
    )
    app = FastAPI()
    app.include_router(limites.router, prefix="/produtos")
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=1),
        tenant_id,
    )
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            produto=produto,
            tenant=tenant_id,
            outro_tenant=outro_tenant,
            permissoes=permissoes,
            db=db,
        )
    db.close()
    engine.dispose()


def consultar(relatorio, **params):
    resposta = relatorio.client.get(
        "/produtos/relatorio/limites-estoque", params=params
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


@pytest.mark.parametrize(
    "atual,minimo,maximo,status,falta,excesso",
    [
        (3.25, 10.5, 20, "abaixo_minimo", 7.25, 0),
        (-2, 10, 20, "abaixo_minimo", 12, 0),
        (0, 10, 20, "abaixo_minimo", 10, 0),
        (10, 10, 20, "no_minimo", 0, 0),
        (20, 10, 20, "dentro_limites", 0, 0),
        (20.25, 10, 20, "acima_maximo", 0, 0.25),
        (200, 10, 0, "dentro_limites", 0, None),
        (200, 0, 0, "sem_limites", None, None),
        (5, None, None, "sem_limites", None, None),
        (25, None, 20, "acima_maximo", None, 5),
        (12, 20, 10, "limites_invalidos", None, None),
        (12, -1, 20, "limites_invalidos", None, None),
    ],
)
def test_calculos_e_limites_inclusivos(
    relatorio, atual, minimo, maximo, status, falta, excesso
):
    relatorio.produto("Ração", atual, minimo, maximo)
    dados = consultar(relatorio)
    item = dados["itens"][0]
    assert (item["situacao"], item["falta_minimo"], item["excesso_maximo"]) == (
        status,
        falta,
        excesso,
    )
    assert dados["resumo"] == {status: 1, "todos": 1}
    assert consultar(relatorio, situacao=status)["total"] == 1
    assert relatorio.permissoes == ["produtos.visualizar", "produtos.visualizar"]


def test_paginacao_exportacao_e_resumo_nao_ficam_limitados_a_pagina(relatorio):
    for nome in ("C", "A", "B"):
        relatorio.produto(nome)
    relatorio.produto("Excesso", atual=30)
    pagina = consultar(relatorio, page_size=2, situacao="abaixo_minimo")
    assert [item["nome"] for item in pagina["itens"]] == ["A", "B"]
    assert (pagina["total"], pagina["total_pages"]) == (3, 2)
    assert pagina["resumo"] == {"abaixo_minimo": 3, "acima_maximo": 1, "todos": 4}
    segunda = consultar(relatorio, page_size=2, page=2, situacao="abaixo_minimo")
    assert [item["nome"] for item in segunda["itens"]] == ["C"]
    exportacao = consultar(
        relatorio, page_size=1, page=2, export_all=True, situacao="abaixo_minimo"
    )
    assert [item["nome"] for item in exportacao["itens"]] == ["A", "B", "C"]
    assert exportacao["total"] == len(exportacao["itens"]) == 3


def test_isolamento_tenant_e_exclusoes_de_estoque(relatorio):
    relatorio.produto("Visível")
    relatorio.produto("Variação", tipo_produto="VARIACAO")
    relatorio.produto("Kit físico", tipo_produto="KIT", tipo_kit="FISICO")
    relatorio.produto("Outra empresa", tenant_id=relatorio.outro_tenant)
    relatorio.produto("Serviço", tipo="servico")
    relatorio.produto("Pai", tipo_produto="PAI")
    relatorio.produto("Virtual", tipo_produto="KIT", tipo_kit="VIRTUAL")
    relatorio.produto("Variação virtual", tipo_produto="VARIACAO", tipo_kit="VIRTUAL")
    relatorio.produto("Inativo", ativo=False)
    dados = consultar(relatorio)
    assert {item["nome"] for item in dados["itens"]} == {
        "Visível",
        "Variação",
        "Kit físico",
    }
    assert consultar(relatorio, ativo="inativos")["itens"][0]["nome"] == "Inativo"
    assert consultar(relatorio, ativo="todos")["total"] == 4
    assert consultar(relatorio, export_all=True)["total"] == 3


def test_busca_saldo_e_filtros_catalogo(relatorio):
    relatorio.db.execute(
        Categoria.__table__.insert().values(
            id=1, nome="Rações", tenant_id=relatorio.tenant, user_id=1
        )
    )
    relatorio.db.execute(
        Marca.__table__.insert().values(
            id=1, nome="Marca A", tenant_id=relatorio.tenant, user_id=1
        )
    )
    relatorio.db.execute(
        Cliente.__table__.insert().values(
            id=1, nome="Fornecedor A", tenant_id=relatorio.tenant, user_id=1
        )
    )
    relatorio.db.commit()
    produto_id = relatorio.produto(
        "Ração especial", atual=0, categoria_id=1, marca_id=1, fornecedor_id=1
    )
    relatorio.produto("Ração negativa", atual=-2)
    relatorio.produto("Ração positiva", atual=5)
    assert consultar(relatorio, saldo="sem_estoque")["total"] == 2
    assert consultar(relatorio, saldo="zerado")["itens"][0]["id"] == produto_id
    assert consultar(relatorio, saldo="negativo")["itens"][0]["estoque_atual"] == -2
    assert consultar(relatorio, busca="especial")["total"] == 1
    for filtro in ("categoria_id", "marca_id", "fornecedor_id"):
        dados = consultar(relatorio, **{filtro: 1})
        assert dados["total"] == 1
        assert dados["itens"][0]["id"] == produto_id
    assert consultar(relatorio, busca="inexistente")["resumo"] == {"todos": 0}


def test_rejeita_filtros_invalidos_e_exige_permissao(relatorio, monkeypatch):
    for params in ({"situacao": "qualquer"}, {"page": 0}, {"page_size": 201}):
        resposta = relatorio.client.get(
            "/produtos/relatorio/limites-estoque", params=params
        )
        assert resposta.status_code == 422

    def negar(*_args, **_kwargs):
        raise HTTPException(status_code=403, detail="Sem permissão")

    monkeypatch.setattr("app.security.permissions_decorator.check_permission", negar)
    assert (
        relatorio.client.get("/produtos/relatorio/limites-estoque").status_code == 403
    )
