"""Filtro por venda preserva os lancamentos da venda sem alterar os totais gerais."""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db import Base
from app.db import base as _base  # noqa: F401 - registra as tabelas relacionadas
from app.financeiro.fluxo_caixa_routes import (
    _mapa_numeros_venda_por_lancamento,
    get_fluxo_caixa,
)
from app.financeiro_models import (
    CategoriaFinanceira,
    ContaBancaria,
    ContaPagar,
    ContaReceber,
    FormaPagamento,
    LancamentoManual,
    Pagamento,
    Recebimento,
)
from app.ia.aba5_models import FluxoCaixa
from app.models import Cliente
from app.vendas_devolucoes_models import VendaDevolucao
from app.vendas_models import Venda, VendaPagamento


@pytest.fixture
def entradas(tenant_context):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[
            model.__table__
            for model in (
                Venda,
                VendaPagamento,
                VendaDevolucao,
                Cliente,
                ContaBancaria,
                CategoriaFinanceira,
                FormaPagamento,
                ContaPagar,
                Pagamento,
                ContaReceber,
                Recebimento,
                LancamentoManual,
                FluxoCaixa,
            )
        ],
    )
    db_session = Session(engine)
    usuario = SimpleNamespace(id=1)
    tenant_id = uuid4()
    tenant_context(tenant_id)
    vendas = []
    for numero, total, status in (
        ("QA-20261016-001", 100, "baixa_parcial"),
        ("QA-20261016-002", 200, "finalizada"),
    ):
        venda = Venda(
            tenant_id=tenant_id,
            user_id=usuario.id,
            vendedor_id=usuario.id,
            numero_venda=numero,
            total=total,
            subtotal=total,
            status=status,
            data_venda=datetime(2026, 10, 16, 10),
        )
        db_session.add(venda)
        db_session.flush()
        vendas.append(venda)
    for venda, valor, status, sufixo in (
        (vendas[0], 40, "realizado", "-REALIZADO"),
        (vendas[0], 60, "previsto", ""),
        (vendas[1], 200, "realizado", ""),
    ):
        db_session.add(
            LancamentoManual(
                tenant_id=tenant_id,
                user_id=usuario.id,
                tipo="entrada",
                valor=Decimal(valor),
                status=status,
                data_lancamento=date(2026, 10, 16),
                descricao="QA espelho de venda",
                documento=f"VENDA-{venda.id}{sufixo}",
            )
        )
    db_session.flush()
    try:
        yield SimpleNamespace(db=db_session, auth=(usuario, tenant_id), vendas=vendas)
    finally:
        db_session.close()
        engine.dispose()


def _fluxo(c, numero=None):
    return get_fluxo_caixa(
        data_inicio="2026-10-01",
        data_fim="2026-10-31",
        numero_venda=numero,
        db=c.db,
        current_user_and_tenant=c.auth,
    )


@pytest.mark.parametrize("numero", ["QA-20261016-001", "001"])
def test_numero_inclui_entrada_e_saldo_por_lancamento_sem_outra_venda(entradas, numero):
    fluxo = _fluxo(entradas, numero)

    assert fluxo.total_realizado_entradas == 40
    assert fluxo.total_previsto_entradas == 60
    assert len(fluxo.movimentacoes) == 2
    assert {m.numero_venda for m in fluxo.movimentacoes} == {"QA-20261016-001"}


def test_sem_numero_preserva_todos_os_totais_e_movimentos(entradas):
    fluxo = _fluxo(entradas)

    assert fluxo.total_realizado_entradas == 240
    assert fluxo.total_previsto_entradas == 60
    assert len(fluxo.movimentacoes) == 3


def test_numero_inexistente_nao_retorna_movimentos_de_outras_vendas(entradas):
    fluxo = _fluxo(entradas, "QA-NUMERO-INEXISTENTE")

    assert fluxo.movimentacoes == []
    assert fluxo.total_realizado_entradas == 0
    assert fluxo.total_previsto_entradas == 0


def test_mapa_busca_uma_vez_e_nao_resolve_documento_de_outra_loja(entradas):
    c = entradas
    resultado = c.db.execute(
        Venda.__table__.insert(),
        {
            "tenant_id": uuid4(),
            "user_id": 1,
            "vendedor_id": 1,
            "numero_venda": "QA-OUTRA-LOJA",
            "subtotal": 99,
            "total": 99,
            "status": "finalizada",
            "data_venda": datetime(2026, 10, 16, 10),
        },
    )
    outra_id = resultado.inserted_primary_key[0]
    lancamentos = c.db.query(LancamentoManual).order_by(LancamentoManual.id).all()
    lancamentos.append(SimpleNamespace(id=999, documento=f"VENDA-{outra_id}"))
    consultas = []

    def registrar(_conn, _cursor, statement, _params, _ctx, _many):
        consultas.append(statement)

    event.listen(c.db.bind, "before_cursor_execute", registrar)
    try:
        mapa = _mapa_numeros_venda_por_lancamento(c.db, c.auth[1], lancamentos)
    finally:
        event.remove(c.db.bind, "before_cursor_execute", registrar)

    assert len(consultas) == 1
    assert set(mapa.values()) == {v.numero_venda for v in c.vendas}
    assert 999 not in mapa
