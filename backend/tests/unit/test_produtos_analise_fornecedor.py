from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import (  # noqa: F401
    caixa_models,
    dre_plano_contas_models,
    ecommerceai_integration_models,
    financeiro_models,
    produto_identidade_models,
)
from app.models import Cliente
from app.produtos import relatorios_analise_routes as analise
from app.produtos_models import (
    Categoria,
    Departamento,
    Marca,
    Produto,
    ProdutoFornecedor,
)
from app.tenancy.context import set_current_tenant
from app.vendas_models import Venda, VendaItem


@pytest.fixture
def relatorio():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    for model in (
        Departamento, Categoria, Marca, Cliente, Produto, ProdutoFornecedor,
        Venda, VendaItem,
    ):
        model.__table__.create(engine)
    db = Session(engine)
    tenant, outro_tenant = uuid4(), uuid4()
    for fornecedor_id, nome in ((1, "Principal"), (2, "QUIMIAGRI")):
        db.execute(Cliente.__table__.insert().values(
            id=fornecedor_id, tenant_id=tenant, user_id=1, nome=nome,
        ))
    db.commit()
    sequencias = {"produto": 0, "venda": 0, "vinculo": 0}

    def produto(nome, **extra):
        sequencias["produto"] += 1
        produto_id = sequencias["produto"]
        dados = dict(
            id=produto_id, tenant_id=tenant, user_id=1, nome=nome,
            codigo=f"SKU-{produto_id}", preco_custo=10, preco_venda=25,
        )
        dados.update(extra)
        db.execute(Produto.__table__.insert().values(**dados))
        db.commit()
        return produto_id

    def vinculo(produto_id, fornecedor_id=2, **extra):
        sequencias["vinculo"] += 1
        dados = dict(
            id=sequencias["vinculo"], tenant_id=tenant, produto_id=produto_id,
            fornecedor_id=fornecedor_id, ativo=True,
        )
        dados.update(extra)
        db.execute(ProdutoFornecedor.__table__.insert().values(**dados))
        db.commit()

    def venda(produto_id, quantidade=2, **extra):
        sequencias["venda"] += 1
        venda_id = sequencias["venda"]
        dados = dict(
            id=venda_id, tenant_id=tenant, numero_venda=f"VEN-{venda_id}",
            vendedor_id=1, user_id=1, status="finalizada", canal="loja_fisica",
            data_venda=datetime(2026, 10, 20, 12), subtotal=quantidade * 25,
            total=quantidade * 25,
        )
        dados.update(extra)
        db.execute(Venda.__table__.insert().values(**dados))
        db.execute(VendaItem.__table__.insert().values(
            id=venda_id, tenant_id=dados["tenant_id"], venda_id=venda_id,
            produto_id=produto_id, tipo="produto", quantidade=quantidade,
            preco_unitario=25, subtotal=quantidade * 25,
        ))
        db.commit()

    filtros = dict(
        categoria_id=None, marca_id=None, departamento_id=None,
        fornecedor_id=2, canal=None, busca=None,
    )
    parametros = dict(
        tenant_id=tenant, access_ids=[tenant], inicio=datetime(2026, 1, 1),
        fim=datetime(2026, 10, 26, 23, 59, 59), filtros=filtros,
    )
    set_current_tenant(tenant)
    yield SimpleNamespace(
        db=db, tenant=tenant, outro_tenant=outro_tenant, produto=produto,
        vinculo=vinculo, venda=venda, parametros=parametros,
    )
    db.close()
    engine.dispose()


def consultar(relatorio, fornecedor_id=2):
    parametros = {
        **relatorio.parametros,
        "filtros": {**relatorio.parametros["filtros"], "fornecedor_id": fornecedor_id},
    }
    return analise._consultar_produtos(relatorio.db, **parametros)


@pytest.mark.parametrize("fornecedor_principal", [None, 1])
def test_inclui_fornecedor_principal_e_alternativo_ativo(relatorio, fornecedor_principal):
    principal = relatorio.produto("Principal", fornecedor_id=2)
    alternativo = relatorio.produto("Alternativo", fornecedor_id=fornecedor_principal)
    relatorio.vinculo(alternativo)
    relatorio.venda(principal)
    relatorio.venda(alternativo, quantidade=3)

    produtos = consultar(relatorio)

    assert {item["produto_id"] for item in produtos} == {principal, alternativo}
    assert sum(item["quantidade"] for item in produtos) == 5
    assert sum(item["faturamento"] for item in produtos) == 125
    assert all(item["fornecedor_id"] == 2 for item in produtos)
    assert all(item["fornecedor_nome"] == "QUIMIAGRI" for item in produtos)


def test_ignora_vinculo_inativo_ou_de_outra_empresa(relatorio):
    inativo = relatorio.produto("Vínculo desativado", fornecedor_id=1)
    externo = relatorio.produto("Vínculo de outra empresa", fornecedor_id=1)
    relatorio.vinculo(inativo, ativo=False)
    relatorio.vinculo(externo, tenant_id=relatorio.outro_tenant)
    relatorio.venda(inativo)
    relatorio.venda(externo)

    assert consultar(relatorio) == []


def test_varios_vinculos_nao_duplicam_itens_receita_ou_numero_vendas(relatorio):
    produto_id = relatorio.produto("Ambos os vínculos", fornecedor_id=2)
    relatorio.vinculo(produto_id)
    relatorio.vinculo(produto_id)
    relatorio.vinculo(produto_id, fornecedor_id=1)
    relatorio.venda(produto_id)
    relatorio.venda(produto_id, quantidade=3)

    [item] = consultar(relatorio)

    assert (item["quantidade"], item["faturamento"], item["vendas"]) == (5, 125, 2)
    assert analise._contar_vendas(relatorio.db, **relatorio.parametros) == 2


def test_sem_filtro_preserva_fornecedor_principal_e_produtos_sem_fornecedor(relatorio):
    alternativo = relatorio.produto("Alternativo", fornecedor_id=1)
    sem_fornecedor = relatorio.produto("Sem fornecedor")
    relatorio.vinculo(alternativo)
    relatorio.venda(alternativo)
    relatorio.venda(sem_fornecedor)

    produtos = {item["produto_id"]: item for item in consultar(relatorio, None)}

    assert produtos[alternativo]["fornecedor_id"] == 1
    assert produtos[alternativo]["fornecedor_nome"] == "Principal"
    assert produtos[sem_fornecedor]["fornecedor_id"] is None


def test_todas_consultas_respeitam_fornecedor_periodo_status_e_empresa(relatorio):
    produto_id = relatorio.produto("Alternativo", fornecedor_id=1)
    relatorio.vinculo(produto_id)
    relatorio.venda(produto_id)
    relatorio.venda(produto_id, status="cancelada")
    relatorio.venda(produto_id, status="devolvida")
    relatorio.venda(produto_id, data_venda=datetime(2025, 12, 31))
    relatorio.venda(produto_id, tenant_id=relatorio.outro_tenant)
    externo = relatorio.produto(
        "Produto inacessível", fornecedor_id=2, tenant_id=relatorio.outro_tenant,
    )
    relatorio.venda(externo)
    sem_fornecedor = relatorio.produto("Não corresponde")
    relatorio.venda(sem_fornecedor)

    [item] = consultar(relatorio)

    assert (item["produto_id"], item["quantidade"], item["faturamento"]) == (
        produto_id, 2, 50,
    )
    assert analise._contar_vendas(relatorio.db, **relatorio.parametros) == 1
    diaria = (
        relatorio.db.query(func.sum(VendaItem.quantidade))
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .join(Produto, Produto.id == VendaItem.produto_id)
    )
    filtros = relatorio.parametros["filtros"]
    parametros = {key: value for key, value in relatorio.parametros.items() if key != "filtros"}
    assert analise._filtros_base(diaria, **parametros, **filtros).scalar() == 2
