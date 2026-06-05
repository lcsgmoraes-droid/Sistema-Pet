import os
from datetime import datetime
from types import SimpleNamespace

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.produtos.listagem import (
    _aplicar_filtro_fornecedores_produtos,
    _aplicar_busca_texto_produtos,
    _aplicar_filtros_basicos_catalogo_produtos,
    _aplicar_filtro_promocao_ativa,
    _departamento_id_produto,
    _fornecedor_nome_produto,
    _montar_resposta_paginada_produtos,
    _nome_area_produto,
    _normalizar_palavras_busca_produto,
    _resolver_fornecedor_ids_filtro,
    _resolver_metricas_valorizacao_produto,
)


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
            SimpleNamespace(ativo=True, e_principal=False, fornecedor=fornecedor_secundario),
            SimpleNamespace(ativo=True, e_principal=True, fornecedor=fornecedor_principal),
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


class _FakeQuery:
    def __init__(self, *, first_result=None, all_result=None):
        self.first_result = first_result
        self.all_result = all_result or []
        self.filters = []

    def filter(self, *criteria):
        self.filters.extend(criteria)
        return self

    def first(self):
        return self.first_result

    def all(self):
        return self.all_result


class _FakeDB:
    def __init__(self, *, grupo=None, fornecedores=None):
        self.grupo = grupo
        self.fornecedores = fornecedores or []

    def query(self, model):
        if getattr(model, "__name__", "") == "FornecedorGrupo":
            return _FakeQuery(first_result=self.grupo)
        return _FakeQuery(all_result=[(fornecedor_id,) for fornecedor_id in self.fornecedores])


def test_resolver_fornecedor_ids_filtro_preserva_fornecedor_direto():
    ids, veio_de_grupo = _resolver_fornecedor_ids_filtro(
        _FakeDB(),
        fornecedor_id=42,
        fornecedor_grupo_id=None,
        tenant_id="tenant-1",
        access_ids=["tenant-1"],
    )

    assert ids == [42]
    assert veio_de_grupo is False


def test_resolver_fornecedor_ids_filtro_busca_fornecedores_do_grupo():
    ids, veio_de_grupo = _resolver_fornecedor_ids_filtro(
        _FakeDB(grupo=SimpleNamespace(id=7), fornecedores=[10, 11]),
        fornecedor_id=None,
        fornecedor_grupo_id=7,
        tenant_id="tenant-1",
        access_ids=["tenant-1", "tenant-parceiro"],
    )

    assert ids == [10, 11]
    assert veio_de_grupo is True


def test_resolver_fornecedor_ids_filtro_rejeita_grupo_inexistente():
    try:
        _resolver_fornecedor_ids_filtro(
            _FakeDB(grupo=None),
            fornecedor_id=None,
            fornecedor_grupo_id=99,
            tenant_id="tenant-1",
            access_ids=["tenant-1"],
        )
    except LookupError as exc:
        assert "Grupo de fornecedor nao encontrado" in str(exc)
    else:
        raise AssertionError("Grupo inexistente deveria gerar LookupError")


def test_aplicar_filtro_fornecedores_produtos_sem_ids_de_grupo_forca_resultado_vazio():
    query = _FakeQuery()

    filtrada = _aplicar_filtro_fornecedores_produtos(
        query,
        fornecedor_ids_filtro=[],
        filtro_por_grupo=True,
    )

    assert filtrada is query
    assert len(query.filters) == 1


def test_normalizar_palavras_busca_produto_remove_espacos_excedentes():
    assert _normalizar_palavras_busca_produto("  golden   gato castrado  ") == [
        "golden",
        "gato",
        "castrado",
    ]


def test_aplicar_busca_texto_produtos_filtra_todas_as_palavras():
    query = _FakeQuery()

    filtrada = _aplicar_busca_texto_produtos(
        query,
        "golden gato",
        lambda palavra: f"condicao:{palavra}",
    )

    assert filtrada is query
    assert query.filters == ["condicao:golden", "condicao:gato"]


def test_aplicar_filtro_promocao_ativa_usa_janela_de_datas():
    query = _FakeQuery()

    filtrada = _aplicar_filtro_promocao_ativa(query, referencia=datetime(2026, 1, 1, 12, 0))

    assert filtrada is query
    assert len(query.filters) == 3


def test_aplicar_filtros_basicos_catalogo_produtos_combina_filtros_opcionais():
    query = _FakeQuery()

    filtrada = _aplicar_filtros_basicos_catalogo_produtos(
        query,
        categoria_id=1,
        marca_id=2,
        departamento_id=3,
        estoque_baixo=True,
    )

    assert filtrada is query
    assert len(query.filters) == 4


def test_montar_resposta_paginada_produtos_calcula_paginas():
    resposta = _montar_resposta_paginada_produtos(
        items=["a", "b"],
        total=101,
        page=2,
        page_size=50,
    )

    assert resposta == {
        "items": ["a", "b"],
        "total": 101,
        "page": 2,
        "page_size": 50,
        "pages": 3,
    }
