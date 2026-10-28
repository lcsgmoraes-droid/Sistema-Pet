import os
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

import app.db.base  # noqa: F401 - registra tambem os relacionamentos de Venda.
from app.db import Base
from app.models import Cliente
from app.produtos import listagem as produtos_listagem
from app.produtos.listagem import (
    _aplicar_filtro_fornecedor_produto,
    _aplicar_filtros_basicos_produtos,
    _departamento_id_produto,
    _fornecedor_nome_produto,
    _load_options_listagem_produtos,
    _nome_area_produto,
    _normalizar_paginacao_produtos,
    _palavras_busca_produto,
    _resolver_metricas_valorizacao_produto,
    _resolver_fornecedor_ids_filtro_produto,
    _tipos_base_listagem,
)
from app.produtos_models import (
    Categoria,
    Departamento,
    Marca,
    Produto,
    ProdutoBlingSync,
    ProdutoImagem,
    ProdutoLote,
    ProdutoProtocoloDose,
    ProdutoProtocoloRecorrencia,
)
from app.tenancy.context import tenant_context


class _FakeQuery:
    def __init__(self, first_result=None, all_result=None):
        self.first_result = first_result
        self.all_result = all_result or []
        self.filters = []

    def filter(self, *expressions):
        self.filters.extend(expressions)
        return self

    def first(self):
        return self.first_result

    def all(self):
        return self.all_result


class _FakeDb:
    def __init__(self, *queries):
        self.queries = list(queries)
        self.query_calls = []

    def query(self, *entities):
        self.query_calls.append(entities)
        if not self.queries:
            raise AssertionError("Consulta inesperada")
        return self.queries.pop(0)


class _FakeProdutoQuery:
    def __init__(self):
        self.filters = []

    def filter(self, *expressions):
        self.filters.append(expressions)
        return self


class _FakeHierarchyQuery:
    def __init__(self, scalar_result=None, all_result=None):
        self.scalar_result = scalar_result
        self.all_result = all_result or []
        self.filters = []
        self.options_args = []
        self.order_by_args = []

    def filter(self, *expressions):
        self.filters.append(expressions)
        return self

    def options(self, *options):
        self.options_args.extend(options)
        return self

    def group_by(self, *_expressions):
        return self

    def order_by(self, *expressions):
        self.order_by_args.extend(expressions)
        return self

    def scalar(self):
        return self.scalar_result

    def all(self):
        return self.all_result


class _FakePageQuery:
    def __init__(self, rows, total=0):
        self.rows = rows
        self.total = total
        self.count_calls = 0
        self.options_args = []
        self.order_by_args = []
        self.offset_arg = None
        self.limit_arg = None
        self.filters = []

    def count(self):
        self.count_calls += 1
        return self.total

    def options(self, *options):
        self.options_args.extend(options)
        return self

    def filter(self, *expressions):
        self.filters.extend(expressions)
        return self

    def order_by(self, *expressions):
        self.order_by_args.extend(expressions)
        return self

    def offset(self, value):
        self.offset_arg = value
        return self

    def limit(self, value):
        self.limit_arg = value
        return self

    def all(self):
        return self.rows


def test_nome_area_produto_prioriza_departamento_direto():
    produto = SimpleNamespace(
        departamento=SimpleNamespace(nome="Racoes"),
        categoria=SimpleNamespace(departamento=SimpleNamespace(nome="Gatos")),
    )

    assert _nome_area_produto(produto) == "Racoes"


def test_nome_area_produto_usa_departamento_da_categoria_como_fallback():
    produto = SimpleNamespace(
        departamento=None,
        categoria=SimpleNamespace(departamento=SimpleNamespace(nome="Higiene")),
    )

    assert _nome_area_produto(produto) == "Higiene"


def test_departamento_id_produto_usa_categoria_quando_produto_nao_tem_setor():
    produto = SimpleNamespace(
        departamento_id=None,
        categoria=SimpleNamespace(departamento_id=77),
    )

    assert _departamento_id_produto(produto) == 77


def test_fornecedor_nome_produto_prioriza_vinculo_principal_ativo():
    fornecedor_principal = SimpleNamespace(nome="Fornecedor Principal")
    fornecedor_secundario = SimpleNamespace(nome="Fornecedor Secundario")
    produto = SimpleNamespace(
        fornecedor=None,
        fornecedores_alternativos=[
            SimpleNamespace(
                ativo=True, e_principal=False, fornecedor=fornecedor_secundario
            ),
            SimpleNamespace(
                ativo=True, e_principal=True, fornecedor=fornecedor_principal
            ),
        ],
    )

    assert _fornecedor_nome_produto(produto) == "Fornecedor Principal"


def test_resolver_metricas_valorizacao_produto_simples_preserva_reservas():
    produto = SimpleNamespace(
        id=10,
        tipo_produto="SIMPLES",
        tipo_kit=None,
        estoque_atual=8,
        preco_custo=4.5,
        preco_venda=9.0,
    )

    metricas = _resolver_metricas_valorizacao_produto(
        db=object(),
        produto=produto,
        reservas_por_produto={10: 3},
    )

    assert metricas == {
        "estoque_atual": 8.0,
        "estoque_reservado": 3.0,
        "estoque_disponivel": 5.0,
        "preco_custo": 4.5,
        "preco_venda": 9.0,
        "valor_custo_total": 36.0,
        "valor_venda_total": 72.0,
    }


def test_palavras_busca_produto_remove_espacos_extras():
    assert _palavras_busca_produto("  racao   gato  85g ") == ["racao", "gato", "85g"]


def test_palavras_busca_produto_aceita_termo_vazio():
    assert _palavras_busca_produto(None) == []
    assert _palavras_busca_produto("   ") == []


def test_montar_query_produtos_vendaveis_aplica_base_status_e_busca():
    assert hasattr(produtos_listagem, "_montar_query_produtos_vendaveis")
    query = _FakeProdutoQuery()
    db = _FakeDb(query)

    resultado = produtos_listagem._montar_query_produtos_vendaveis(
        db,
        tenant_id="tenant-principal",
        termo_busca="golden gato",
        contar_total=False,
    )

    assert resultado is query
    assert len(db.query_calls) == 1
    assert len(query.filters) == 3
    assert len(query.filters[0]) == 3


def test_montar_query_listagem_produtos_aplica_base_status_e_busca():
    assert hasattr(produtos_listagem, "_montar_query_listagem_produtos")
    query = _FakeProdutoQuery()
    db = _FakeDb(query)

    resultado = produtos_listagem._montar_query_listagem_produtos(
        db,
        tenant_ids=["tenant-principal", "tenant-parceiro"],
        termo_busca="racao senior",
        ativo=True,
        tipo_produto=None,
        produto_predecessor_id=None,
        include_variations=True,
        busca_completa=True,
    )

    assert resultado is query
    assert len(db.query_calls) == 1
    assert len(query.filters) == 4
    assert len(query.filters[0]) == 2
    assert len(query.filters[1]) == 1


def test_montar_query_listagem_produtos_prioriza_predecessor_sobre_tipo():
    assert hasattr(produtos_listagem, "_montar_query_listagem_produtos")
    query = _FakeProdutoQuery()
    db = _FakeDb(query)

    resultado = produtos_listagem._montar_query_listagem_produtos(
        db,
        tenant_ids=["tenant-principal"],
        termo_busca="",
        ativo=None,
        tipo_produto="KIT",
        produto_predecessor_id=42,
        include_variations=True,
        busca_completa=False,
    )

    filtro_base = " ".join(str(expressao) for expressao in query.filters[0])
    assert resultado is query
    assert len(query.filters) == 1
    assert "produto_predecessor_id" in filtro_base
    assert "tipo_produto" not in filtro_base


def test_expandir_produtos_listagem_conta_e_inclui_variacoes_quando_solicitado(
    monkeypatch,
):
    assert hasattr(produtos_listagem, "_expandir_produtos_listagem")
    produto_pai = SimpleNamespace(
        id=10,
        tipo_produto="PAI",
        tenant_id="tenant-principal",
        categoria=None,
    )
    variacao = SimpleNamespace(
        id=11,
        tipo_produto="VARIACAO",
        produto_pai_id=10,
        tenant_id="tenant-principal",
        categoria=None,
    )
    produto_simples = SimpleNamespace(
        id=12,
        tipo_produto="SIMPLES",
        tenant_id="tenant-principal",
        categoria=None,
    )
    count_query = _FakeHierarchyQuery(all_result=[(10, 1)])
    variations_query = _FakeHierarchyQuery(all_result=[variacao])
    db = _FakeDb(count_query, variations_query)
    enriquecidos = []

    def fake_enriquecer(_db, produto, tenant_id, reservas, **kwargs):
        enriquecidos.append((produto.id, tenant_id, reservas, kwargs))
        produto.enriquecido = True
        return produto

    monkeypatch.setattr(
        produtos_listagem, "_enriquecer_produto_listagem", fake_enriquecer
    )
    monkeypatch.setattr(
        produtos_listagem,
        "_mapa_validade_proxima_produtos",
        lambda _db, produtos, tenant_ids: {
            produto.id: {"validade_proxima_listagem": f"validade-{produto.id}"}
            for produto in produtos
        },
    )

    resultado = produtos_listagem._expandir_produtos_listagem(
        db,
        [produto_pai, produto_simples],
        tenant_id="tenant-principal",
        access_ids=["tenant-principal"],
        reservas_por_produto={10: 2.0},
        incluir_detalhes_composto=False,
        include_variations=True,
        termo_busca="",
        load_options=["joinedload-fake"],
        validade_por_produto={10: {"validade_proxima_listagem": "validade-10"}},
    )

    assert resultado == [produto_pai, variacao, produto_simples]
    assert produto_pai.total_variacoes == 1
    assert variations_query.options_args == ["joinedload-fake"]
    assert len(enriquecidos) == 3
    assert enriquecidos[0][3]["validade_por_produto"] == {
        10: {"validade_proxima_listagem": "validade-10"}
    }
    assert enriquecidos[1][3]["validade_por_produto"] == {
        11: {"validade_proxima_listagem": "validade-11"}
    }


def test_expandir_produtos_listagem_nao_busca_variacoes_durante_busca(monkeypatch):
    assert hasattr(produtos_listagem, "_expandir_produtos_listagem")
    produto_pai = SimpleNamespace(
        id=10,
        tipo_produto="PAI",
        tenant_id="tenant-principal",
        categoria=None,
    )
    count_query = _FakeHierarchyQuery(all_result=[(10, 3)])
    db = _FakeDb(count_query)

    monkeypatch.setattr(
        produtos_listagem,
        "_enriquecer_produto_listagem",
        lambda _db, produto, *_args, **_kwargs: produto,
    )

    resultado = produtos_listagem._expandir_produtos_listagem(
        db,
        [produto_pai],
        tenant_id="tenant-principal",
        access_ids=["tenant-principal"],
        reservas_por_produto={},
        incluir_detalhes_composto=True,
        include_variations=True,
        termo_busca="racao",
        load_options=[],
        validade_por_produto={},
    )

    assert resultado == [produto_pai]
    assert produto_pai.total_variacoes == 3
    assert len(db.query_calls) == 1


def test_buscar_pagina_produtos_listagem_aplica_total_ordenacao_e_paginacao():
    assert hasattr(produtos_listagem, "_buscar_pagina_produtos_listagem")
    produto = SimpleNamespace(id=10)
    query = _FakePageQuery([produto, None], total=7)

    produtos, total, load_options = produtos_listagem._buscar_pagina_produtos_listagem(
        query,
        termo_busca="golden",
        offset=20,
        page_size=10,
        incluir_imagens=False,
        incluir_lotes=True,
        contar_total=True,
    )

    assert produtos == [produto]
    assert produtos is not query.rows
    assert total == 7
    assert query.count_calls == 1
    assert query.offset_arg == 20
    assert query.limit_arg == 10
    assert load_options
    assert query.options_args == load_options
    assert query.order_by_args


def test_buscar_pagina_produtos_listagem_permite_total_posterior():
    assert hasattr(produtos_listagem, "_buscar_pagina_produtos_listagem")
    produto = SimpleNamespace(id=11)
    query = _FakePageQuery([produto], total=99)

    produtos, total, _load_options = produtos_listagem._buscar_pagina_produtos_listagem(
        query,
        termo_busca="",
        offset=0,
        page_size=50,
        incluir_imagens=True,
        incluir_lotes=False,
        contar_total=False,
    )

    assert produtos == [produto]
    assert total is None
    assert query.count_calls == 0
    assert query.offset_arg == 0
    assert query.limit_arg == 50


def test_buscar_pagina_produtos_listagem_rapida_ordena_candidatos_em_memoria():
    produto_nome = SimpleNamespace(
        id=10,
        nome="Premier Gatos",
        codigo="SKU-10",
        codigo_barras=None,
        codigos_barras_alternativos=None,
    )
    produto_codigo = SimpleNamespace(
        id=11,
        nome="Outro produto",
        codigo="premier",
        codigo_barras=None,
        codigos_barras_alternativos=None,
    )
    query = _FakePageQuery([produto_nome, produto_codigo], total=99)

    produtos, total, _load_options = produtos_listagem._buscar_pagina_produtos_listagem(
        query,
        termo_busca="premier",
        offset=0,
        page_size=12,
        incluir_imagens=False,
        incluir_lotes=False,
        contar_total=False,
        busca_rapida=True,
    )

    assert produtos == [produto_codigo, produto_nome]
    assert total is None
    assert query.count_calls == 0
    assert query.order_by_args == []
    assert query.filters
    assert query.limit_arg == 120


@pytest.mark.parametrize("ordenacao", ["estoque_desc", "estoque_asc"])
def test_buscar_pagina_produtos_listagem_ordena_por_estoque_com_desempate_recente(
    ordenacao,
):
    query = _FakePageQuery([], total=0)

    produtos_listagem._buscar_pagina_produtos_listagem(
        query,
        termo_busca="",
        ordenacao=ordenacao,
        offset=0,
        page_size=20,
        incluir_imagens=False,
        incluir_lotes=False,
    )

    assert len(query.order_by_args) == 3
    assert "estoque_atual" in str(query.order_by_args[0])
    assert "created_at" in str(query.order_by_args[1])


def test_montar_resposta_produtos_paginados_calcula_pages_e_total():
    assert hasattr(produtos_listagem, "_montar_resposta_produtos_paginados")
    produto = SimpleNamespace(id=10)

    resposta = produtos_listagem._montar_resposta_produtos_paginados(
        [produto],
        total=21,
        page=2,
        page_size=10,
        offset=10,
    )

    assert resposta == {
        "items": [produto],
        "total": 21,
        "page": 2,
        "page_size": 10,
        "pages": 3,
    }


def test_montar_resposta_produtos_paginados_estima_total_quando_nao_contou():
    assert hasattr(produtos_listagem, "_montar_resposta_produtos_paginados")
    produtos = [SimpleNamespace(id=10), SimpleNamespace(id=11)]

    resposta = produtos_listagem._montar_resposta_produtos_paginados(
        produtos,
        total=None,
        page=3,
        page_size=2,
        offset=4,
    )

    assert resposta["items"] == produtos
    assert resposta["total"] == 6
    assert resposta["pages"] == 3


def test_tipos_base_listagem_preserva_variacoes_apenas_em_busca():
    assert _tipos_base_listagem(include_variations=False, termo_busca="racao") == [
        "SIMPLES"
    ]
    assert _tipos_base_listagem(include_variations=True, termo_busca=None) == [
        "SIMPLES",
        "PAI",
        "KIT",
    ]
    assert _tipos_base_listagem(include_variations=True, termo_busca="racao") == [
        "SIMPLES",
        "PAI",
        "KIT",
        "VARIACAO",
    ]


def test_resolver_fornecedor_ids_filtro_produto_prioriza_grupo_e_usa_tenants_informados():
    db = _FakeDb(
        _FakeQuery(first_result=SimpleNamespace(id=7)),
        _FakeQuery(all_result=[(11,), (12,)]),
    )

    ids, filtro_por_grupo = _resolver_fornecedor_ids_filtro_produto(
        db,
        tenant_id="tenant-principal",
        fornecedor_id=99,
        fornecedor_grupo_id=7,
        tenant_ids_fornecedores=["tenant-principal", "tenant-parceiro"],
    )

    assert ids == [11, 12]
    assert filtro_por_grupo is True
    assert len(db.query_calls) == 2


def test_resolver_fornecedor_ids_filtro_produto_retorna_fornecedor_direto_sem_consultar_db():
    db = _FakeDb()

    ids, filtro_por_grupo = _resolver_fornecedor_ids_filtro_produto(
        db,
        tenant_id="tenant-principal",
        fornecedor_id=33,
        fornecedor_grupo_id=None,
    )

    assert ids == [33]
    assert filtro_por_grupo is False
    assert db.query_calls == []


def test_resolver_fornecedor_ids_filtro_produto_levanta_404_para_grupo_inexistente():
    db = _FakeDb(_FakeQuery(first_result=None))

    with pytest.raises(HTTPException) as exc_info:
        _resolver_fornecedor_ids_filtro_produto(
            db,
            tenant_id="tenant-principal",
            fornecedor_id=None,
            fornecedor_grupo_id=999,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Grupo de fornecedor nao encontrado"


def test_aplicar_filtro_fornecedor_produto_forca_sem_resultado_quando_grupo_vazio():
    query = _FakeProdutoQuery()

    resultado = _aplicar_filtro_fornecedor_produto(
        query,
        fornecedor_ids=[],
        filtro_por_grupo=True,
    )

    assert resultado is query
    assert len(query.filters) == 1


def test_aplicar_filtro_fornecedor_produto_ignora_quando_nao_ha_filtro():
    query = _FakeProdutoQuery()

    resultado = _aplicar_filtro_fornecedor_produto(
        query,
        fornecedor_ids=[],
        filtro_por_grupo=False,
    )

    assert resultado is query
    assert query.filters == []


def test_aplicar_filtros_basicos_produtos_ignora_quando_nao_ha_filtros():
    query = _FakeProdutoQuery()

    resultado = _aplicar_filtros_basicos_produtos(
        query,
        categoria_id=None,
        marca_id=None,
        departamento_id=None,
        estoque_baixo=False,
        em_promocao=False,
    )

    assert resultado is query
    assert query.filters == []


def test_aplicar_filtros_basicos_produtos_aplica_filtros_disponiveis():
    query = _FakeProdutoQuery()

    resultado = _aplicar_filtros_basicos_produtos(
        query,
        categoria_id=1,
        marca_id=2,
        departamento_id=3,
        estoque_baixo=True,
        em_promocao=True,
        referencia=datetime(2026, 6, 8, 10, 0, 0),
    )

    assert resultado is query
    assert len(query.filters) == 5


@pytest.mark.parametrize("estoque_situacao", ["com_estoque", "sem_estoque"])
def test_aplicar_filtros_basicos_produtos_filtra_situacao_estoque(
    estoque_situacao,
):
    query = _FakeProdutoQuery()

    resultado = _aplicar_filtros_basicos_produtos(
        query,
        categoria_id=None,
        marca_id=None,
        departamento_id=None,
        estoque_baixo=False,
        em_promocao=False,
        estoque_situacao=estoque_situacao,
    )

    assert resultado is query
    assert len(query.filters) == 1


@pytest.mark.parametrize("imagem_situacao", ["com_foto", "sem_foto"])
def test_aplicar_filtros_basicos_produtos_filtra_situacao_imagem(
    imagem_situacao,
):
    query = _FakeProdutoQuery()

    resultado = _aplicar_filtros_basicos_produtos(
        query,
        categoria_id=None,
        marca_id=None,
        departamento_id=None,
        estoque_baixo=False,
        em_promocao=False,
        imagem_situacao=imagem_situacao,
    )

    assert resultado is query
    assert len(query.filters) == 1
    expressao = str(query.filters[0][0])
    assert "imagem_principal" in expressao
    assert "trim" in expressao.lower()


def test_normalizar_paginacao_produtos_limita_page_size_e_calcula_offset():
    assert _normalizar_paginacao_produtos(page=3, page_size=500, max_page_size=200) == (
        3,
        200,
        400,
    )


def test_normalizar_paginacao_produtos_corrige_valores_minimos():
    assert _normalizar_paginacao_produtos(page=-2, page_size=0, max_page_size=50) == (
        1,
        1,
        0,
    )


def test_load_options_listagem_produtos_monta_lista_nova_com_relacionamentos_base():
    opcoes = _load_options_listagem_produtos(incluir_imagens=True, incluir_lotes=False)
    outra_lista = _load_options_listagem_produtos(
        incluir_imagens=True, incluir_lotes=False
    )

    assert opcoes is not outra_lista
    opcoes.clear()
    assert outra_lista


@pytest.fixture
def produto_com_relacionamentos_db():
    engine = create_engine("sqlite://")
    modelos = [
        Departamento,
        Categoria,
        Marca,
        Cliente,
        Produto,
        ProdutoImagem,
        ProdutoLote,
        ProdutoBlingSync,
        ProdutoProtocoloRecorrencia,
        ProdutoProtocoloDose,
    ]
    Base.metadata.create_all(engine, tables=[modelo.__table__ for modelo in modelos])
    tenant_id = uuid4()
    dados = [
        (Departamento, {"nome": "Racoes", "user_id": 1}),
        (Categoria, {"nome": "Gatos", "departamento_id": 1, "user_id": 1}),
        (Marca, {"nome": "Marca de teste", "user_id": 1}),
        (Cliente, {"nome": "Fornecedor", "tipo_pessoa": "PJ", "user_id": 1}),
        (
            Produto,
            {
                "codigo": "SKU-1",
                "nome": "Produto de teste",
                "categoria_id": 1,
                "marca_id": 1,
                "fornecedor_id": 1,
                "user_id": 1,
            },
        ),
        (ProdutoImagem, {"produto_id": 1, "url": "/uploads/produtos/teste.jpg"}),
        (
            ProdutoLote,
            {
                "produto_id": 1,
                "nome_lote": "Lote de teste",
                "quantidade_inicial": 10,
                "quantidade_disponivel": 7,
                "ordem_entrada": 1,
            },
        ),
        (ProdutoBlingSync, {"produto_id": 1, "bling_produto_id": "bling-1"}),
        (
            ProdutoProtocoloRecorrencia,
            {"produto_id": 1, "nome": "Vacinacao", "tipo": "protocolo_doses"},
        ),
        (
            ProdutoProtocoloDose,
            {"protocolo_id": 1, "numero_dose": 1, "dias_desde_inicio": 0},
        ),
    ]
    with engine.begin() as connection:
        for modelo, valores in dados:
            connection.execute(
                modelo.__table__.insert(), {"id": 1, "tenant_id": tenant_id, **valores}
            )

    consultas = []

    def registrar_select(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            consultas.append(statement)

    event.listen(engine, "before_cursor_execute", registrar_select)
    try:
        with sessionmaker(bind=engine)() as db, tenant_context(tenant_id):
            yield db, consultas
    finally:
        event.remove(engine, "before_cursor_execute", registrar_select)
        engine.dispose()


@pytest.mark.parametrize("incluir_imagens", [False, True])
@pytest.mark.parametrize("incluir_lotes", [False, True])
@pytest.mark.parametrize("incluir_bling_sync", [False, True])
def test_load_options_listagem_produtos_carrega_dados_e_respeita_flags(
    produto_com_relacionamentos_db, incluir_imagens, incluir_lotes, incluir_bling_sync
):
    db, consultas = produto_com_relacionamentos_db
    opcoes = _load_options_listagem_produtos(
        incluir_imagens=incluir_imagens,
        incluir_lotes=incluir_lotes,
        incluir_bling_sync=incluir_bling_sync,
    )
    produto = db.query(Produto).options(*opcoes).one()
    consultas_apos_carregar = len(consultas)

    assert produto.categoria.nome == "Gatos"
    assert produto.marca.nome == "Marca de teste"
    assert [protocolo.nome for protocolo in produto.protocolos_recorrencia] == [
        "Vacinacao"
    ]
    assert [dose.numero_dose for dose in produto.protocolos_recorrencia[0].doses] == [1]
    assert [imagem.url for imagem in produto.imagens] == (
        ["/uploads/produtos/teste.jpg"] if incluir_imagens else []
    )
    assert [lote.nome_lote for lote in produto.lotes] == (
        ["Lote de teste"] if incluir_lotes else []
    )
    if incluir_bling_sync:
        assert produto.bling_sync.bling_produto_id == "bling-1"
    else:
        assert produto.bling_sync is None
    assert len(consultas) == consultas_apos_carregar

    # Departamento e fornecedor conservam o carregamento lazy padrao; o helper
    # nao deve remover seus dados nem assumir que fazem parte do eager load.
    assert _nome_area_produto(produto) == "Racoes"
    assert produto.categoria.departamento.nome == "Racoes"
    assert _fornecedor_nome_produto(produto) == "Fornecedor"
