from copy import deepcopy
from types import SimpleNamespace
from uuid import UUID
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user_and_tenant
from app.db import Base
from app.db import base as _base  # noqa: F401 - registra todo o metadata
from app.db import get_session
from app.models import Tenant, User
from app.grupo_comercial_models import (
    GrupoComercial,
    GrupoComercialEstoqueCompartilhado,
    GrupoComercialMembro,
)
from app.produtos_catalogo_models import Produto, ProdutoHistoricoAlteracao
from app.produto_identidade_models import (
    ProdutoIdentidade,
    ProdutoIdentidadeHistoricoAlteracao,
)
from app.produtos import cadastro_routes
from app.produtos_models import ProdutoProtocoloRecorrencia
from app.security import permissions_decorator
from app.veterinario_models import VetPartnerLink
from app.services.produto_historico_service import registrar_alteracoes_produto
from app.tenancy.context import (
    clear_current_tenant,
    set_current_tenant,
    tenant_context,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            ProdutoHistoricoAlteracao.__table__,
            Produto.__table__,
            VetPartnerLink.__table__,
            GrupoComercial.__table__,
            GrupoComercialMembro.__table__,
            GrupoComercialEstoqueCompartilhado.__table__,
        ],
    )
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def test_origem_do_produto_nao_pode_ser_trocada():
    loja = uuid4()
    produto = Produto(tenant_id=loja, nome="Racao", codigo="SKU1")
    produto.origem_tenant_id = loja
    with pytest.raises(ValueError):
        produto.origem_tenant_id = uuid4()


def test_historico_registra_so_campos_base_alterados(db):
    loja = uuid4()
    total = registrar_alteracoes_produto(
        db,
        produto_id=5,
        tenant_id=loja,
        user_id=2,
        antes={"nome": "Racao A", "codigo_barras": "789", "preco_venda": 10.0},
        depois={"nome": "Racao B", "codigo_barras": "789", "preco_venda": 12.0},
    )
    db.commit()

    assert total == 1
    set_current_tenant(loja)
    registro = db.query(ProdutoHistoricoAlteracao).one()
    clear_current_tenant()
    assert (registro.campo, registro.valor_anterior, registro.valor_novo) == (
        "nome",
        "Racao A",
        "Racao B",
    )
    assert registro.user_id == 2


@pytest.fixture
def cadastro_api(monkeypatch):
    """PUT e servicos de identidade reais; apenas autenticacao e permissao isoladas."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    tables = {
        Base.metadata.tables[name]
        for name in (
            "produtos",
            "produtos_historico_alteracoes",
            "produto_identidades",
            "produto_identidades_historico_alteracoes",
            "produto_sku_aliases",
            "produto_imagens",
            "produto_lotes",
            "produto_kit_componentes",
            "grupos_comerciais",
            "grupo_comercial_membros",
        )
    }
    tables.update(
        {GrupoComercialEstoqueCompartilhado.__table__, VetPartnerLink.__table__}
    )
    tables.add(ProdutoProtocoloRecorrencia.__table__)
    tables.add(ProdutoProtocoloRecorrencia.doses.property.mapper.local_table)
    while True:
        dependencies = {
            fk.column.table for table in tables for fk in table.foreign_keys
        }
        if dependencies.issubset(tables):
            break
        tables.update(dependencies)
    Base.metadata.create_all(engine, tables=list(tables))
    db_session = Session(engine)
    loja = Tenant(id=str(uuid4()), name="Loja A ficticia", name_normalized="lojaa")
    outra_loja = Tenant(
        id=str(uuid4()), name="Loja B ficticia", name_normalized="lojab"
    )
    db_session.add_all([loja, outra_loja])
    db_session.flush()
    tenant = UUID(loja.id)
    outro_tenant = UUID(outra_loja.id)
    set_current_tenant(tenant)
    usuario = User(
        tenant_id=tenant,
        email="operador@example.invalid",
        hashed_password="not-an-authenticated-password",
        nome="Operador ficticio",
    )
    db_session.add(usuario)
    db_session.flush()
    grupo = GrupoComercial(
        nome="Grupo ficticio do teste de cadastro",
        criado_por_empresa_id=loja.id,
        criado_por_usuario_id=usuario.id,
    )
    db_session.add(grupo)
    db_session.flush()
    db_session.add_all(
        [
            GrupoComercialMembro(
                grupo_id=grupo.id, empresa_id=loja.id, papel="responsavel"
            ),
            GrupoComercialMembro(grupo_id=grupo.id, empresa_id=outra_loja.id),
        ]
    )
    produto = Produto(
        tenant_id=tenant,
        user_id=usuario.id,
        codigo="018631.1",
        nome="Produto ficticio do piloto",
        descricao_curta='<p class="teste">Descricao <strong>original</strong>.</p>',
        descricao_completa="Descricao completa ficticia",
        codigo_barras="4006381333931",
        gtin_ean="4006381333931",
        unidade="UN",
        preco_venda=65,
        preco_app=71,
        preco_ecommerce=72,
        preco_ifood=66,
        estoque_atual=31,
        estoque_maximo=0,
        anunciar_app=True,
        anunciar_ecommerce=True,
        anunciar_ifood=True,
        ifood_pausado=False,
    )
    with tenant_context(tenant):
        db_session.add(produto)
        db_session.flush()
    vizinho = Produto(
        tenant_id=outro_tenant,
        user_id=usuario.id,
        codigo="OUTRO-PRODUTO-FICTICIO",
        nome="Produto de outra loja",
        preco_venda=89,
        estoque_atual=7,
        ifood_pausado=False,
    )
    with tenant_context(outro_tenant):
        db_session.add(vizinho)
        db_session.flush()
    set_current_tenant(tenant)

    def permissao(_db, user_id, permission, tenant_id, **_kwargs):
        assert user_id == usuario.id
        assert permission == "produtos.editar"
        assert tenant_id == tenant

    monkeypatch.setattr(permissions_decorator, "check_permission", permissao)
    app = FastAPI()
    app.include_router(cadastro_routes.router, prefix="/produtos")
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (usuario, tenant)
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(
                client=client,
                db=db_session,
                produto=produto,
                vizinho=vizinho,
                tenant=tenant,
                outro_tenant=outro_tenant,
            )
    finally:
        db_session.close()
        engine.dispose()


def _snapshot_produto(produto, *, except_fields=()):
    return deepcopy(
        {
            column.key: getattr(produto, column.key)
            for column in Produto.__table__.columns
            if column.key not in except_fields
        }
    )


@pytest.mark.parametrize("identidade_preexistente", [False, True])
def test_put_pausa_com_ean_inalterado_nao_cria_nem_vincula_identidade(
    cadastro_api, identidade_preexistente
):
    api = cadastro_api
    if identidade_preexistente:
        # Uma identidade orfa com o mesmo EAN tampouco autoriza vinculo num no-op.
        api.db.add(
            ProdutoIdentidade(
                tenant_id=api.tenant,
                origem_tenant_id=api.tenant,
                nome="Identidade preexistente preservada",
                codigo_barras=api.produto.codigo_barras,
                gtin_ean=api.produto.gtin_ean,
                chave_matching=api.produto.codigo_barras,
            )
        )
        api.db.flush()
    antes = _snapshot_produto(
        api.produto, except_fields={"updated_at", "ifood_pausado"}
    )
    with tenant_context(api.outro_tenant):
        vizinho_antes = _snapshot_produto(api.vizinho)
    for pausa in (True, False):
        response = api.client.put(
            f"/produtos/{api.produto.id}",
            json={
                "ifood_pausado": pausa,
                "nome": api.produto.nome,
                "descricao_curta": api.produto.descricao_curta,
                "codigo_barras": api.produto.codigo_barras,
                "gtin_ean": api.produto.gtin_ean,
                "unidade": api.produto.unidade,
            },
        )
        assert response.status_code == 200, response.text
        api.db.expire_all()
        assert api.produto.ifood_pausado is pausa
        assert response.json()["produto_identidade_id"] is None
        assert (
            _snapshot_produto(
                api.produto, except_fields={"updated_at", "ifood_pausado"}
            )
            == antes
        )
        assert api.db.query(ProdutoIdentidade).count() == int(identidade_preexistente)
        assert api.db.query(ProdutoHistoricoAlteracao).count() == 0
        assert api.db.query(ProdutoIdentidadeHistoricoAlteracao).count() == 0
        with tenant_context(api.outro_tenant):
            assert _snapshot_produto(api.vizinho) == vizinho_antes


@pytest.mark.parametrize("campo", ["codigo_barras", "gtin_ean"])
def test_put_identificador_realmente_editado_continua_criando_identidade(
    cadastro_api, campo, monkeypatch
):
    api = cadastro_api
    if campo == "codigo_barras":
        # O validador de unicidade usa SQL PostgreSQL (::text/ANY). Isolamos
        # apenas essa consulta dialetal; PUT, persistencia e identidade sao reais.
        # Este teste nao pretende provar a unicidade de codigos de barras.
        monkeypatch.setattr(
            cadastro_routes, "_validar_codigo_barras_unico", lambda *_args, **_kw: None
        )
    # GTIN e a chave quando nao existe codigo de barras comercial.
    if campo == "gtin_ean":
        api.produto.codigo_barras = None
        api.db.flush()
    novo_ean = "5901234123457"
    response = api.client.put(f"/produtos/{api.produto.id}", json={campo: novo_ean})
    assert response.status_code == 200, response.text
    api.db.expire_all()
    identidade = api.db.query(ProdutoIdentidade).one()
    assert api.produto.produto_identidade_id == identidade.id
    assert identidade.chave_matching == novo_ean
    assert getattr(identidade, campo) == novo_ean
    assert identidade.descricao_curta == api.produto.descricao_curta
    assert api.produto.preco_venda == 65 and api.produto.preco_ifood == 66


def test_put_campo_compartilhado_editado_propaga_sem_reenviar_campos_inalterados(
    cadastro_api,
):
    api = cadastro_api
    identidade = ProdutoIdentidade(
        tenant_id=api.tenant,
        origem_tenant_id=api.tenant,
        nome=api.produto.nome,
        descricao_curta="Fonte compartilhada preservada",
        codigo_barras=api.produto.codigo_barras,
        gtin_ean=api.produto.gtin_ean,
        chave_matching=api.produto.codigo_barras,
    )
    api.db.add(identidade)
    api.db.flush()
    api.produto.produto_identidade_id = identidade.id
    with tenant_context(api.outro_tenant):
        api.vizinho.produto_identidade_id = identidade.id
        api.vizinho.descricao_curta = identidade.descricao_curta
        api.db.flush()
        protegido = _snapshot_produto(api.vizinho, except_fields={"nome", "updated_at"})
    response = api.client.put(
        f"/produtos/{api.produto.id}",
        json={
            "nome": "Nome compartilhado realmente editado",
            "descricao_curta": api.produto.descricao_curta,
            "codigo_barras": api.produto.codigo_barras,
            "gtin_ean": api.produto.gtin_ean,
            "ifood_pausado": True,
        },
    )
    assert response.status_code == 200, response.text
    api.db.expire_all()
    assert identidade.nome == api.produto.nome == "Nome compartilhado realmente editado"
    assert identidade.descricao_curta == "Fonte compartilhada preservada"
    assert api.produto.ifood_pausado is True
    historico = api.db.query(ProdutoIdentidadeHistoricoAlteracao).all()
    assert [(item.campo, item.valor_novo) for item in historico] == [
        ("nome", "Nome compartilhado realmente editado")
    ]
    with tenant_context(api.outro_tenant):
        assert api.vizinho.nome == identidade.nome
        assert (
            _snapshot_produto(api.vizinho, except_fields={"nome", "updated_at"})
            == protegido
        )
