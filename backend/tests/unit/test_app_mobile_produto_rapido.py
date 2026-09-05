from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_session
from app.produtos_models import Produto
from app.routes import app_mobile_funcionario_produtos_routes as routes
from app.routes.app_mobile_funcionario_pdv import auth
from app.routes.ecommerce_auth import _get_current_ecommerce_user

TENANT_A = UUID("44e1e23b-782a-4466-8a27-5d38a8925021")
TENANT_B = UUID("d3202f99-8fa8-48e5-9c99-c586562ab840")
PAYLOAD = {
    "codigo_barras": "7891234567890",
    "nome": "Ração teste 10 kg",
    "preco_venda": 175.55,
}


@pytest.fixture
def ambiente(db_session, monkeypatch, tenant_context):
    tenant_context(TENANT_A)
    user = SimpleNamespace(id=1, tenant_id=TENANT_A, permitido=True)
    monkeypatch.setattr(
        auth,
        "get_cliente_for_app_profile_or_none",
        lambda _db, usuario, perfil: (
            SimpleNamespace(id=10)
            if usuario.permitido and perfil == "funcionario"
            else None
        ),
    )
    app = FastAPI()
    app.include_router(routes.router, prefix="/app")
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[_get_current_ecommerce_user] = lambda: user
    with TestClient(app) as client:
        yield client, db_session, user


def consultar(client, codigo=PAYLOAD["codigo_barras"]):
    return client.get(
        "/app/funcionario/produtos/consultar-codigo", params={"codigo": codigo}
    )


def cadastrar(client, **campos):
    return client.post("/app/funcionario/produtos/rapido", json={**PAYLOAD, **campos})


def test_cadastra_minimo_e_fica_disponivel_para_completar_no_erp(ambiente):
    client, db, _ = ambiente
    resposta = consultar(client)
    assert resposta.status_code == 200
    assert resposta.json() is None
    criado = cadastrar(client, nome="  Ração teste 10 kg  ")
    assert criado.status_code == 201, criado.text
    dados = criado.json()
    assert dados["nome"] == "Ração teste 10 kg"
    assert dados["preco_venda"] == 175.55
    assert dados["codigo"].startswith("APP-")
    assert consultar(client).json()["id"] == dados["id"]
    # Leitura da mesma tabela usada pelo cadastro completo do ERP.
    produto = (
        db.execute(select(Produto.__table__).where(Produto.id == dados["id"]))
        .mappings()
        .one()
    )
    assert str(produto["tenant_id"]) == str(TENANT_A)
    assert produto["user_id"] == 1
    assert produto["estoque_atual"] == 0
    assert produto["preco_custo"] == 0
    assert produto["anunciar_app"] is False
    assert produto["anunciar_ecommerce"] is False
    assert produto["tipo_produto"] == "SIMPLES"


def test_tentar_salvar_novamente_nao_duplica_nem_sobrescreve(ambiente):
    client, db, _ = ambiente
    primeira = cadastrar(client)
    segunda = cadastrar(client, nome="Outro nome", preco_venda=10)
    assert primeira.status_code == 201, primeira.text
    assert segunda.status_code == 409, segunda.text
    assert segunda.json()["detail"]["produto"]["id"] == primeira.json()["id"]
    produtos = db.execute(select(Produto.__table__)).mappings().all()
    assert len(produtos) == 1
    assert produtos[0]["nome"] == PAYLOAD["nome"]
    assert produtos[0]["preco_venda"] == PAYLOAD["preco_venda"]


@pytest.mark.parametrize(
    "campo,valor,consulta",
    [
        ("codigo_barras", "0012345678905", "012345678905"),
        ("gtin_ean", "7891234567890", "7891234567890"),
        ("gtin_ean_tributario", "7891234567890", "7891234567890"),
        (
            "codigos_barras_alternativos",
            '["7891234567890", "7899999999999"]',
            "7891234567890",
        ),
        ("codigo", "SKU-ABC-1", "sku-abc-1"),
        ("codigos_barras_alternativos", '["CODIGO-Abc"]', "codigo-abc"),
    ],
)
def test_localiza_inativo_por_eans_sku_e_bloqueia_novo_cadastro(
    ambiente, campo, valor, consulta
):
    client, db, _ = ambiente
    db.execute(
        Produto.__table__.insert().values(
            **{
                "tenant_id": TENANT_A,
                "user_id": 1,
                "codigo": "ANTIGO",
                "nome": "Produto antigo",
                "ativo": False,
                "situacao": False,
                "preco_venda": 20,
                campo: valor,
            },
        )
    )
    db.commit()
    encontrado = consultar(client, consulta)
    assert encontrado.status_code == 200, encontrado.text
    assert encontrado.json()["nome"] == "Produto antigo"
    assert encontrado.json()["ativo"] is False
    assert cadastrar(client, codigo_barras=consulta).status_code == 409


def test_codigo_parcial_nao_e_confundido_com_ean_alternativo(ambiente):
    client, db, _ = ambiente
    db.execute(
        Produto.__table__.insert().values(
            tenant_id=TENANT_A,
            user_id=1,
            codigo="ANTIGO",
            nome="Outro produto",
            codigos_barras_alternativos='["1234567890123"]',
        )
    )
    db.commit()
    assert consultar(client, "12345678").json() is None


def test_nao_consulta_ou_bloqueia_produtos_de_outra_empresa(ambiente):
    client, db, _ = ambiente
    db.execute(
        Produto.__table__.insert().values(
            tenant_id=TENANT_B,
            user_id=1,
            codigo="OUTRA",
            nome="Produto de outra empresa",
            codigo_barras=PAYLOAD["codigo_barras"],
        )
    )
    db.commit()
    assert consultar(client).json() is None
    assert cadastrar(client).status_code == 201


def test_cliente_sem_perfil_operacional_nao_consulta_nem_cadastra(ambiente):
    client, _, user = ambiente
    user.permitido = False
    assert consultar(client).status_code == 403
    assert cadastrar(client).status_code == 403


@pytest.mark.parametrize(
    "invalido",
    [
        {"nome": "   "},
        {"nome": "a" * 201},
        {"codigo_barras": "@invalido"},
        {"codigo_barras": "1" * 21},
        {"preco_venda": 0},
        {"preco_venda": -1},
        {"preco_venda": "NaN"},
        {"preco_venda": "Infinity"},
        {"preco_venda": 1.111},
        {"preco_custo": -1},
        {"unidade": "INVALIDA"},
        {"tenant_id": str(TENANT_B)},
        {"estoque_atual": 100},
        {"anunciar_app": True},
    ],
)
def test_rejeita_dados_invalidos_e_campos_fora_do_cadastro_rapido(ambiente, invalido):
    client, _, _ = ambiente
    assert cadastrar(client, **invalido).status_code == 422


def test_aceita_custo_e_unidade(ambiente):
    client, db, _ = ambiente
    criado = cadastrar(client, preco_custo=112.35, unidade="CX")
    assert criado.status_code == 201, criado.text
    assert criado.json()["unidade"] == "CX"
    produto = db.execute(select(Produto.__table__)).mappings().one()
    assert produto["preco_custo"] == 112.35


def test_produto_legado_com_unidade_ou_status_nulo_tambem_bloqueia_duplicidade(
    ambiente,
):
    client, db, _ = ambiente
    db.execute(
        Produto.__table__.insert().values(
            tenant_id=TENANT_A,
            user_id=1,
            codigo="LEGADO",
            nome="Legado",
            codigo_barras=PAYLOAD["codigo_barras"],
            unidade=None,
            ativo=None,
        )
    )
    db.commit()
    resposta = consultar(client)
    assert resposta.status_code == 200
    assert resposta.json()["unidade"] == "UN"
    assert cadastrar(client).status_code == 409
