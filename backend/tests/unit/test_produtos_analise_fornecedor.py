from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, func
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
        Departamento,
        Categoria,
        Marca,
        Cliente,
        Produto,
        ProdutoFornecedor,
        Venda,
        VendaItem,
    ):
        model.__table__.create(engine)
    db = Session(engine)
    tenant, outro_tenant = uuid4(), uuid4()
    for fornecedor_id, nome in ((1, "Principal"), (2, "QUIMIAGRI")):
        db.execute(
            Cliente.__table__.insert().values(
                id=fornecedor_id,
                tenant_id=tenant,
                user_id=1,
                nome=nome,
            )
        )
    db.commit()
    sequencias = {"produto": 0, "venda": 0, "vinculo": 0}

    def produto(nome, **extra):
        sequencias["produto"] += 1
        produto_id = sequencias["produto"]
        dados = dict(
            id=produto_id,
            tenant_id=tenant,
            user_id=1,
            nome=nome,
            codigo=f"SKU-{produto_id}",
            preco_custo=10,
            preco_venda=25,
        )
        dados.update(extra)
        db.execute(Produto.__table__.insert().values(**dados))
        db.commit()
        return produto_id

    def vinculo(produto_id, fornecedor_id=2, **extra):
        sequencias["vinculo"] += 1
        dados = dict(
            id=sequencias["vinculo"],
            tenant_id=tenant,
            produto_id=produto_id,
            fornecedor_id=fornecedor_id,
            ativo=True,
        )
        dados.update(extra)
        db.execute(ProdutoFornecedor.__table__.insert().values(**dados))
        db.commit()

    def venda(produto_id, quantidade=2, **extra):
        sequencias["venda"] += 1
        venda_id = sequencias["venda"]
        dados = dict(
            id=venda_id,
            tenant_id=tenant,
            numero_venda=f"VEN-{venda_id}",
            vendedor_id=1,
            user_id=1,
            status="finalizada",
            canal="loja_fisica",
            data_venda=datetime(2026, 10, 20, 12),
            subtotal=quantidade * 25,
            total=quantidade * 25,
        )
        dados.update(extra)
        db.execute(Venda.__table__.insert().values(**dados))
        db.execute(
            VendaItem.__table__.insert().values(
                id=venda_id,
                tenant_id=dados["tenant_id"],
                venda_id=venda_id,
                produto_id=produto_id,
                tipo="produto",
                quantidade=quantidade,
                preco_unitario=25,
                subtotal=quantidade * 25,
            )
        )
        db.commit()

    filtros = dict(
        categoria_id=None,
        marca_id=None,
        departamento_id=None,
        fornecedor_id=2,
        canal=None,
        busca=None,
    )
    parametros = dict(
        tenant_id=tenant,
        access_ids=[tenant],
        inicio=datetime(2026, 1, 1),
        fim=datetime(2026, 10, 26, 23, 59, 59),
        filtros=filtros,
    )
    set_current_tenant(tenant)
    yield SimpleNamespace(
        db=db,
        tenant=tenant,
        outro_tenant=outro_tenant,
        produto=produto,
        vinculo=vinculo,
        venda=venda,
        parametros=parametros,
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
def test_inclui_fornecedor_principal_e_alternativo_ativo(
    relatorio, fornecedor_principal
):
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
        "Produto inacessível",
        fornecedor_id=2,
        tenant_id=relatorio.outro_tenant,
    )
    relatorio.venda(externo)
    sem_fornecedor = relatorio.produto("Não corresponde")
    relatorio.venda(sem_fornecedor)

    [item] = consultar(relatorio)

    assert (item["produto_id"], item["quantidade"], item["faturamento"]) == (
        produto_id,
        2,
        50,
    )
    assert analise._contar_vendas(relatorio.db, **relatorio.parametros) == 1
    diaria = (
        relatorio.db.query(func.sum(VendaItem.quantidade))
        .select_from(VendaItem)
        .join(Venda, Venda.id == VendaItem.venda_id)
        .join(Produto, Produto.id == VendaItem.produto_id)
    )
    filtros = relatorio.parametros["filtros"]
    parametros = {
        key: value for key, value in relatorio.parametros.items() if key != "filtros"
    }
    assert analise._filtros_base(diaria, **parametros, **filtros).scalar() == 2


def cadastrar_vendedor(relatorio, vendedor_id, nome, **extra):
    relatorio.db.execute(
        Cliente.__table__.insert().values(
            id=vendedor_id,
            tenant_id=extra.pop("tenant_id", relatorio.tenant),
            user_id=1,
            nome=nome,
            is_funcionario=True,
            **extra,
        )
    )
    relatorio.db.commit()


def test_vendedores_usa_vendedor_comercial_legado_e_sem_vendedor(relatorio):
    cadastrar_vendedor(relatorio, 101, "Ana")
    cadastrar_vendedor(relatorio, 102, "Bruno")
    produto_id = relatorio.produto("Produto por vendedor", fornecedor_id=2)
    relatorio.venda(
        produto_id, quantidade=3, vendedor_funcionario_id=101, funcionario_id=102
    )
    relatorio.venda(produto_id, quantidade=2, funcionario_id=102)
    # vendedor_id=1 e o operador; nao deve aparecer como vendedor do produto.
    relatorio.venda(produto_id, quantidade=1)

    vendedores = analise._consultar_vendedores_por_produto(
        relatorio.db, **relatorio.parametros
    )[produto_id]
    [produto] = consultar(relatorio)

    assert vendedores == [
        {
            "vendedor_id": 101,
            "vendedor_nome": "Ana",
            "quantidade": 3,
            "faturamento": 75,
            "participacao_faturamento_pct": 50,
        },
        {
            "vendedor_id": 102,
            "vendedor_nome": "Bruno",
            "quantidade": 2,
            "faturamento": 50,
            "participacao_faturamento_pct": 33.33,
        },
        {
            "vendedor_id": None,
            "vendedor_nome": "Sem vendedor informado",
            "quantidade": 1,
            "faturamento": 25,
            "participacao_faturamento_pct": 16.67,
        },
    ]
    assert sum(item["quantidade"] for item in vendedores) == produto["quantidade"]
    assert sum(item["faturamento"] for item in vendedores) == produto["faturamento"]


def test_vendedores_preserva_homonimos_e_funcionario_inativo(relatorio):
    cadastrar_vendedor(relatorio, 101, "Ana", ativo=False)
    cadastrar_vendedor(relatorio, 102, "Ana")
    produto_id = relatorio.produto("Produto", fornecedor_id=2)
    relatorio.venda(produto_id, quantidade=3, vendedor_funcionario_id=101)
    relatorio.venda(produto_id, quantidade=2, vendedor_funcionario_id=102)

    vendedores = analise._consultar_vendedores_por_produto(
        relatorio.db, **relatorio.parametros
    )[produto_id]

    assert [item["vendedor_id"] for item in vendedores] == [101, 102]
    assert [item["faturamento"] for item in vendedores] == [75, 50]


def test_vendedores_respeita_filtros_sem_duplicar_fornecedores(relatorio):
    cadastrar_vendedor(relatorio, 101, "Ana")
    for model in (Categoria, Marca, Departamento):
        relatorio.db.execute(
            model.__table__.insert().values(
                id=10, tenant_id=relatorio.tenant, user_id=1, nome="Grupo"
            )
        )
    relatorio.db.commit()
    produto_id = relatorio.produto(
        "Produto selecionado", categoria_id=10, marca_id=10, departamento_id=10
    )
    relatorio.vinculo(produto_id)
    relatorio.vinculo(produto_id)
    relatorio.venda(produto_id, vendedor_funcionario_id=101)
    for extra in (
        {"status": "cancelada"},
        {"status": "devolvida"},
        {"canal": "ecommerce"},
        {"data_venda": datetime(2025, 12, 31)},
        {"tenant_id": relatorio.outro_tenant},
    ):
        relatorio.venda(produto_id, vendedor_funcionario_id=101, **extra)
    for extra in (
        {"categoria_id": None},
        {"marca_id": None},
        {"departamento_id": None},
        {"nome": "Outro nome"},
        {"tenant_id": relatorio.outro_tenant},
    ):
        cadastro = dict(
            nome="Produto selecionado", categoria_id=10, marca_id=10, departamento_id=10
        )
        cadastro.update(extra)
        outro = relatorio.produto(**cadastro)
        relatorio.vinculo(outro)
        relatorio.venda(outro, vendedor_funcionario_id=101)
    parametros = {
        **relatorio.parametros,
        "filtros": {
            **relatorio.parametros["filtros"],
            "categoria_id": 10,
            "marca_id": 10,
            "departamento_id": 10,
            "canal": "loja_fisica",
            "busca": "selecionado",
        },
    }

    resultado = analise._consultar_vendedores_por_produto(relatorio.db, **parametros)

    assert list(resultado) == [produto_id]
    assert resultado[produto_id][0]["quantidade"] == 2
    assert resultado[produto_id][0]["faturamento"] == 50


def test_vendedores_nao_expoe_cadastro_de_outra_empresa(relatorio):
    cadastrar_vendedor(
        relatorio, 101, "Nome de outra empresa", tenant_id=relatorio.outro_tenant
    )
    produto_id = relatorio.produto("Produto", fornecedor_id=2)
    relatorio.venda(produto_id, vendedor_funcionario_id=101)

    [vendedor] = analise._consultar_vendedores_por_produto(
        relatorio.db, **relatorio.parametros
    )[produto_id]

    assert vendedor["vendedor_id"] is None
    assert vendedor["vendedor_nome"] == "Sem vendedor informado"
    assert vendedor["faturamento"] == 50


def test_vendedores_preserva_quantidade_fracionada_subtotal_e_receita_zero(relatorio):
    cadastrar_vendedor(relatorio, 101, "Ana")
    produto_id = relatorio.produto("Fracionado", fornecedor_id=2)
    relatorio.venda(produto_id, quantidade=0.375, vendedor_funcionario_id=101)
    relatorio.db.execute(VendaItem.__table__.update().values(subtotal=7.20))
    outro_id = relatorio.produto("Sem receita", fornecedor_id=2)
    relatorio.venda(outro_id, quantidade=0.625, vendedor_funcionario_id=101)
    relatorio.db.execute(
        VendaItem.__table__.update()
        .where(VendaItem.produto_id == outro_id)
        .values(subtotal=0)
    )
    relatorio.db.commit()

    resultado = analise._consultar_vendedores_por_produto(
        relatorio.db, **relatorio.parametros
    )

    assert resultado[produto_id][0]["quantidade"] == 0.375
    assert resultado[produto_id][0]["faturamento"] == 7.20
    assert resultado[produto_id][0]["participacao_faturamento_pct"] == 100
    assert resultado[outro_id][0]["quantidade"] == 0.625
    assert resultado[outro_id][0]["faturamento"] == 0
    assert resultado[outro_id][0]["participacao_faturamento_pct"] == 0


def test_vendedores_faz_uma_consulta_para_todos_produtos(relatorio):
    cadastrar_vendedor(relatorio, 101, "Ana")
    for indice in range(8):
        produto_id = relatorio.produto(f"Produto {indice}", fornecedor_id=2)
        relatorio.venda(produto_id, vendedor_funcionario_id=101)
    consultas = []
    engine = relatorio.db.get_bind()

    def registrar(_conn, _cursor, statement, _parameters, _context, _executemany):
        consultas.append(statement)

    event.listen(engine, "before_cursor_execute", registrar)
    try:
        resultado = analise._consultar_vendedores_por_produto(
            relatorio.db, **relatorio.parametros
        )
    finally:
        event.remove(engine, "before_cursor_execute", registrar)

    assert len(resultado) == 8
    assert len(consultas) == 1
