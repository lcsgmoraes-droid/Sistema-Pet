from datetime import datetime
import re
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import get_session
from app.produto_identity_models import ProdutoSkuAlias
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoHistoricoPreco
from app.routes import app_mobile_funcionario_estoque_routes as estoque
from app.routes import app_mobile_funcionario_produtos_routes as cadastro
from app.routes.app_mobile_funcionario_pdv import auth
from app.routes.ecommerce_auth import _get_current_ecommerce_user

TENANT_A = UUID("44e1e23b-782a-4466-8a27-5d38a8925021")
TENANT_B = UUID("d3202f99-8fa8-48e5-9c99-c586562ab840")


def inserir(db, produto_id=1, **campos):
    db.execute(
        Produto.__table__.insert().values(
            **{
                "id": produto_id,
                "tenant_id": TENANT_A,
                "user_id": 1,
                "codigo": f"SKU-{produto_id}",
                "nome": "Ração original",
                "codigo_barras": "7891234567890",
                "descricao_curta": "Descrição existente",
                "preco_venda": 179.9,
                "preco_custo": 110,
                "estoque_atual": 7,
                "gtin_ean": "7891111111111",
                "ativo": True,
                "situacao": True,
                "codigos_barras_alternativos": '["7892222222222"]',
                **campos,
            }
        )
    )
    db.commit()


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
    if db_session.get_bind().dialect.name == "sqlite":
        # Em producao, o driver PostgreSQL aceita UUID textual e regexp_replace.
        # Adaptar somente essas diferencas para executar a busca real no SQLite.
        def acesso_estoque(db, usuario):
            funcionario, tenant_id = auth._get_funcionario_operacional_or_403(
                db, usuario
            )
            return funcionario, UUID(tenant_id)

        monkeypatch.setattr(
            estoque, "_get_funcionario_operacional_or_403", acesso_estoque
        )
        db_session.connection().connection.driver_connection.create_function(
            "regexp_replace",
            4,
            lambda value, pattern, replacement, flags: re.sub(
                pattern, replacement, value
            ),
        )
    app = FastAPI()
    app.include_router(cadastro.router, prefix="/app")
    app.include_router(estoque.router, prefix="/app")
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[_get_current_ecommerce_user] = lambda: user
    inserir(db_session)
    with TestClient(app) as client:
        yield client, db_session, user


def editar(client, produto_id=1, **campos):
    return client.patch(f"/app/funcionario/produtos/{produto_id}/cadastro", json=campos)


def registro(db, produto_id=1):
    return dict(
        db.execute(select(Produto.__table__).where(Produto.id == produto_id))
        .mappings()
        .one()
    )


def test_edita_cadastro_real_e_novo_ean_localiza_mesmo_produto_sem_movimentar(ambiente):
    client, db, _ = ambiente
    antes = registro(db)
    consulta = client.get("/app/funcionario/produtos/1/cadastro")
    assert consulta.status_code == 200
    assert consulta.json()["descricao_curta"] == "Descrição existente"
    resposta = editar(
        client,
        nome="  Ração corrigida  ",
        codigo_barras=" 0012345678905 ",
        descricao_curta="Nova descrição",
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["nome"] == "Ração corrigida"
    assert resposta.json()["codigo_barras"] == "0012345678905"
    assert resposta.json()["descricao_curta"] == "Nova descrição"
    depois = registro(db)
    alteraveis = {"nome", "codigo_barras", "descricao_curta", "updated_at"}
    assert {k: v for k, v in antes.items() if k not in alteraveis} == {
        k: v for k, v in depois.items() if k not in alteraveis
    }
    assert db.scalar(select(func.count()).select_from(EstoqueMovimentacao)) == 0
    encontrado = client.get("/app/funcionario/estoque/produtos/barcode/0012345678905")
    assert encontrado.status_code == 200, encontrado.text
    assert encontrado.json()["id"] == 1
    assert encontrado.json()["nome"] == "Ração corrigida"
    assert (
        client.get(
            "/app/funcionario/estoque/produtos/barcode/7891234567890"
        ).status_code
        == 404
    )
    busca = client.get(
        "/app/funcionario/estoque/produtos/buscar", params={"q": "Ração corrigida"}
    )
    assert [p["id"] for p in busca.json()] == [1]


def test_edita_preco_registra_historico_e_consultas_do_app_recebem_valor_novo(ambiente):
    client, db, _ = ambiente

    consulta = client.get("/app/funcionario/produtos/1/cadastro")
    assert consulta.status_code == 200
    assert consulta.json()["preco_venda"] == 179.9

    resposta = editar(client, preco_venda=189.9)

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["preco_venda"] == 189.9
    assert registro(db)["preco_venda"] == 189.9
    historico = db.scalar(
        select(ProdutoHistoricoPreco).where(
            ProdutoHistoricoPreco.produto_id == 1,
            ProdutoHistoricoPreco.motivo == "edicao_app_funcionario",
        )
    )
    assert historico is not None
    assert historico.preco_venda_anterior == 179.9
    assert historico.preco_venda_novo == 189.9

    encontrado = client.get("/app/funcionario/estoque/produtos/barcode/7891234567890")
    assert encontrado.status_code == 200, encontrado.text
    assert encontrado.json()["preco_venda"] == 189.9


def test_patch_preserva_campos_omitidos_e_permite_adicionar_ou_limpar_ean(ambiente):
    client, db, _ = ambiente
    assert editar(client, nome="Apenas nome").status_code == 200
    assert registro(db)["descricao_curta"] == "Descrição existente"
    assert registro(db)["codigo_barras"] == "7891234567890"
    assert editar(client, codigo_barras="  ", descricao_curta="").status_code == 200
    assert registro(db)["codigo_barras"] is None
    assert registro(db)["descricao_curta"] is None
    assert editar(client, codigo_barras="7893333333333").status_code == 200
    assert registro(db)["codigo_barras"] == "7893333333333"


@pytest.mark.parametrize(
    "campo,valor,leitura",
    [
        ("codigo_barras", "0012345678905", "012345678905"),
        ("gtin_ean", "7894444444444", "7894444444444"),
        ("gtin_ean_tributario", "7894444444444", "7894444444444"),
        ("codigos_barras_alternativos", '["7894444444444"]', "7894444444444"),
        ("codigo", "SKU-ABC", "sku-abc"),
    ],
)
def test_bloqueia_codigo_de_outro_produto_inclusive_inativo_sem_salvar_parcial(
    ambiente, campo, valor, leitura
):
    client, db, _ = ambiente
    inserir(db, 2, **{campo: valor, "ativo": False})
    antes = registro(db)
    resposta = editar(client, nome="Não deve mudar", codigo_barras=leitura)
    assert resposta.status_code == 409, resposta.text
    assert registro(db) == antes


def test_ean_do_proprio_produto_nao_oculta_colisao_com_outro(ambiente):
    client, db, _ = ambiente
    inserir(db, 2, codigo_barras="7891111111111")
    assert editar(client, codigo_barras="7891111111111").status_code == 409
    # Sem o outro cadastro, o proprio EAN fiscal pode virar o codigo principal.
    db.execute(Produto.__table__.delete().where(Produto.id == 2))
    db.commit()
    assert editar(client, codigo_barras="7891111111111").status_code == 200


def test_alias_de_outro_produto_tambem_bloqueia_edicao(ambiente):
    client, db, _ = ambiente
    inserir(db, 2, codigo_barras=None)
    db.execute(
        ProdutoSkuAlias.__table__.insert().values(
            tenant_id=TENANT_A,
            produto_id=2,
            sku="CODIGO-ANTIGO",
            sku_normalizado="codigo-antigo",
            user_id=1,
            origem="confirmacao_manual",
            motivo="Teste",
        )
    )
    db.commit()
    assert editar(client, codigo_barras="codigo-antigo").status_code == 409


def test_respeita_empresa_perfil_e_produto_arquivado(ambiente):
    client, db, user = ambiente
    inserir(db, 2, tenant_id=TENANT_B, codigo_barras="7894444444444")
    assert client.get("/app/funcionario/produtos/2/cadastro").status_code == 404
    assert editar(client, produto_id=2, nome="Invasão").status_code == 404
    assert editar(client, codigo_barras="7894444444444").status_code == 200
    user.permitido = False
    assert client.get("/app/funcionario/produtos/1/cadastro").status_code == 403
    assert editar(client, nome="Sem permissão").status_code == 403
    user.permitido = True
    inserir(db, 3, deleted_at=datetime.now())
    assert editar(client, produto_id=3, nome="Arquivado").status_code == 404


@pytest.mark.parametrize(
    "campos",
    [
        {"nome": None},
        {"nome": "   "},
        {"nome": "a" * 201},
        {"descricao_curta": "a" * 1001},
        {"codigo_barras": "1" * 21},
        {"codigo_barras": "https://site@produto"},
        {"preco_venda": 0},
        {"preco_venda": 100000000},
        {"estoque_atual": 100},
        {"codigo": "NOVO-SKU"},
        {"tenant_id": str(TENANT_B)},
    ],
)
def test_rejeita_dados_invalidos_e_campos_fora_da_edicao(ambiente, campos):
    client, db, _ = ambiente
    antes = registro(db)
    assert editar(client, **campos).status_code == 422
    assert registro(db) == antes
