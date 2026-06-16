import os
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

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
    assert len(opcoes) == 4
    assert all(
        str(opcao.path).startswith("ORM Path[Mapper[Produto(produtos)]")
        for opcao in opcoes
    )


def test_load_options_listagem_produtos_preserva_quantidade_ao_alternar_flags():
    sem_imagens_com_lotes = _load_options_listagem_produtos(
        incluir_imagens=False,
        incluir_lotes=True,
    )

    assert len(sem_imagens_com_lotes) == 4
