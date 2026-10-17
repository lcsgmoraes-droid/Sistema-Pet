"""Invariantes de estoque reproduzidas por HTTP na copia local pos PR1511."""

import json
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra relacionamentos
from app import estoque_movimentacoes_edicao_routes as edicao
from app.estoque_entrada_manual_routes import EntradaEstoqueRequest
from app.estoque_saida_manual_routes import SaidaEstoqueRequest
from app.grupo_comercial_models import (
    GrupoComercial,
    GrupoComercialEstoqueCompartilhado,
    GrupoComercialMembro,
)
from app.produtos.schemas import ProdutoCreate, ProdutoResponse, ProdutoUpdate
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.variacoes_routes import (
    VariationCreateSchema,
    VariationResponseSchema,
    VariationUpdateSchema,
)
from app.veterinario_models import VetPartnerLink


TENANT = UUID("15110000-0000-0000-0000-000000000001")


@pytest.mark.parametrize("valor", [-1, "NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("schema", [ProdutoCreate, ProdutoUpdate])
def test_custo_produto_invalido_rejeitado_na_escrita(schema, valor):
    dados = {"preco_custo": valor}
    if schema is ProdutoCreate:
        dados.update(codigo="QA1511EST", nome="Produto QA", preco_venda=10)
    with pytest.raises(ValidationError):
        schema(**dados)


@pytest.mark.parametrize("valor", [-1, "NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("campo", ["preco_venda", "preco_custo"])
@pytest.mark.parametrize("schema", [VariationCreateSchema, VariationUpdateSchema])
def test_precos_variacao_invalidos_rejeitados_na_escrita(schema, campo, valor):
    dados = {"preco_venda": 20, campo: valor}
    if schema is VariationCreateSchema:
        dados.update(codigo="QA1511EST", variation_attributes={"cor": "Azul"})
    with pytest.raises(ValidationError):
        schema(**dados)


@pytest.mark.parametrize("valor", [0, -1, "NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize(
    "schema",
    [EntradaEstoqueRequest, SaidaEstoqueRequest, edicao.UpdateMovimentacaoRequest],
)
def test_quantidades_invalidas_nao_chegam_a_mutacao(schema, valor):
    with pytest.raises(ValidationError):
        schema(produto_id=1, quantidade=valor)


def test_leitura_legada_nao_recebe_restricao_de_preco_da_escrita():
    dados = dict(
        id=1,
        codigo="QA1511EST",
        nome="Produto legado",
        preco_custo=-2,
        preco_venda=-1,
        created_at=datetime(2026, 10, 16),
    )
    produto = ProdutoResponse(**dados, ativo=True, updated_at=datetime(2026, 10, 16))
    variacao = VariationResponseSchema(
        **dados,
        variation_attributes={"cor": "Azul"},
        variation_signature="cor:Azul",
        estoque_atual=0,
        codigo_barras=None,
        situacao=True,
    )
    for leitura in (produto, variacao):
        assert leitura.preco_custo == -2
        assert leitura.preco_venda == -1


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            Produto.__table__,
            ProdutoLote.__table__,
            EstoqueMovimentacao.__table__,
            VetPartnerLink.__table__,
            GrupoComercial.__table__,
            GrupoComercialMembro.__table__,
            GrupoComercialEstoqueCompartilhado.__table__,
        ],
    )
    set_current_tenant(TENANT)
    monkeypatch.setattr(edicao, "_agendar_sync_bling", lambda *args: None)
    with Session(engine, autoflush=False, expire_on_commit=False) as session:
        session.execute(
            Produto.__table__.insert(),
            {
                "id": 1,
                "tenant_id": TENANT,
                "user_id": 1,
                "codigo": "QA1511EST",
                "nome": "Produto QA",
                "estoque_atual": 6.75,
                "preco_custo": 14,
                "preco_venda": 30,
            },
        )
        session.execute(
            ProdutoLote.__table__.insert(),
            [
                {
                    "id": 1,
                    "tenant_id": TENANT,
                    "produto_id": 1,
                    "nome_lote": "INICIAL",
                    "quantidade_inicial": 5,
                    "quantidade_disponivel": 3.75,
                    "ordem_entrada": 1,
                    "status": "ativo",
                },
                {
                    "id": 2,
                    "tenant_id": TENANT,
                    "produto_id": 1,
                    "nome_lote": "SEGUNDO",
                    "quantidade_inicial": 3,
                    "quantidade_disponivel": 3,
                    "ordem_entrada": 2,
                    "status": "ativo",
                },
            ],
        )
        session.execute(
            EstoqueMovimentacao.__table__.insert(),
            [
                {
                    "id": 1,
                    "tenant_id": TENANT,
                    "produto_id": 1,
                    "user_id": 1,
                    "tipo": "entrada",
                    "quantidade": 3,
                    "quantidade_anterior": 5,
                    "quantidade_nova": 8,
                    "custo_unitario": 14,
                    "valor_total": 42,
                    "lote_id": 2,
                    "lotes_consumidos": None,
                },
                {
                    "id": 2,
                    "tenant_id": TENANT,
                    "produto_id": 1,
                    "user_id": 1,
                    "tipo": "saida",
                    "quantidade": 1.25,
                    "quantidade_anterior": 8,
                    "quantidade_nova": 6.75,
                    "custo_unitario": 14,
                    "valor_total": 17.5,
                    "lote_id": None,
                    "lotes_consumidos": json.dumps(
                        [{"lote_id": 1, "quantidade": 1.25}]
                    ),
                },
            ],
        )
        session.commit()
        try:
            yield session
        finally:
            clear_current_tenant()
    engine.dispose()


def editar(db, id, **dados):
    return edicao.editar_movimentacao(
        id,
        edicao.UpdateMovimentacaoRequest(**dados),
        db,
        (SimpleNamespace(id=1), TENANT),
    )


def test_editar_entrada_recalcula_total_e_tamanho_do_lote(db):
    editar(db, 1, quantidade=4)
    mov = db.get(EstoqueMovimentacao, 1)
    lote = db.get(ProdutoLote, 2)
    assert mov.valor_total == 56
    assert db.get(Produto, 1).estoque_atual == 7.75
    assert lote.quantidade_inicial == lote.quantidade_disponivel == 4


def test_editar_saida_acima_saldo_rejeita_e_preserva_tudo(db):
    with pytest.raises(HTTPException) as exc:
        editar(db, 2, quantidade=100)
    assert exc.value.status_code == 400
    assert db.get(Produto, 1).estoque_atual == 6.75
    assert db.get(EstoqueMovimentacao, 2).quantidade == 1.25
    assert db.get(ProdutoLote, 1).quantidade_disponivel == 3.75


def test_excluir_saida_restaura_todos_lotes_fifo(db):
    edicao.excluir_movimentacao(2, db, (SimpleNamespace(id=1), TENANT))
    assert db.get(Produto, 1).estoque_atual == 8
    assert db.get(ProdutoLote, 1).quantidade_disponivel == 5
    assert db.get(ProdutoLote, 2).quantidade_disponivel == 3
    assert db.get(EstoqueMovimentacao, 2) is None


def test_editar_saida_recompoe_fifo_sem_perder_quantidade(db):
    editar(db, 2, quantidade=6)
    mov = db.get(EstoqueMovimentacao, 2)
    assert mov.valor_total == 84
    assert db.get(Produto, 1).estoque_atual == 2
    assert db.get(ProdutoLote, 1).quantidade_disponivel == 0
    assert db.get(ProdutoLote, 1).status == "esgotado"
    assert db.get(ProdutoLote, 2).quantidade_disponivel == 2
    assert [c["quantidade"] for c in json.loads(mov.lotes_consumidos)] == [5, 1]
    edicao.excluir_movimentacao(2, db, (SimpleNamespace(id=1), TENANT))
    assert db.get(ProdutoLote, 1).quantidade_disponivel == 5
    assert db.get(ProdutoLote, 2).quantidade_disponivel == 3


def test_edicao_custo_zero_mantem_total_zero(db):
    editar(db, 1, custo_unitario=0)
    assert db.get(EstoqueMovimentacao, 1).valor_total == 0


@pytest.mark.parametrize(
    "referencia", sorted(edicao.REFERENCIAS_AUTOMATICAS_PROTEGIDAS)
)
def test_origem_clinica_protegida_continua_imutavel(db, referencia):
    mov = db.get(EstoqueMovimentacao, 2)
    mov.referencia_tipo = referencia
    db.commit()
    for acao in (
        lambda: editar(db, 2, quantidade=2),
        lambda: edicao.excluir_movimentacao(2, db, (SimpleNamespace(id=1), TENANT)),
    ):
        with pytest.raises(HTTPException) as exc:
            acao()
        assert exc.value.status_code == 409
        assert db.get(Produto, 1).estoque_atual == 6.75


def test_lote_consumido_de_outro_produto_nao_e_alterado(db):
    db.execute(
        Produto.__table__.insert(),
        {
            "id": 2,
            "tenant_id": TENANT,
            "user_id": 1,
            "codigo": "QA1511EST-OUTRO",
            "nome": "Outro produto QA",
            "estoque_atual": 7,
            "preco_custo": 5,
            "preco_venda": 10,
        },
    )
    db.execute(
        ProdutoLote.__table__.insert(),
        {
            "id": 99,
            "tenant_id": TENANT,
            "produto_id": 2,
            "nome_lote": "OUTRO",
            "quantidade_inicial": 7,
            "quantidade_disponivel": 7,
            "ordem_entrada": 3,
            "status": "ativo",
        },
    )
    mov = db.get(EstoqueMovimentacao, 2)
    mov.lotes_consumidos = json.dumps([{"lote_id": 99, "quantidade": 1.25}])
    db.commit()
    with pytest.raises(HTTPException) as exc:
        edicao.excluir_movimentacao(2, db, (SimpleNamespace(id=1), TENANT))
    assert exc.value.status_code == 409
    assert db.get(Produto, 1).estoque_atual == 6.75
    assert db.get(Produto, 2).estoque_atual == 7
    assert db.get(ProdutoLote, 99).quantidade_disponivel == 7
