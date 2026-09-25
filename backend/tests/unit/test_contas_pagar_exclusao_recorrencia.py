from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm import Session

from app.financeiro.contas_pagar_manutencao_routes import excluir_conta_pagar
from app.financeiro.contas_pagar_recorrencia_routes import (
    excluir_recorrencias_contas_pagar,
)
from app.financeiro.contas_pagar_schemas import ContaPagarRecorrenciaBulkDelete
from app.financeiro_models import ContaPagar, LancamentoManual, Pagamento


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for model in (ContaPagar, Pagamento, LancamentoManual):
            connection.exec_driver_sql(
                str(CreateTable(model.__table__).compile(engine))
            )
    with Session(engine) as session:
        yield session
    engine.dispose()


def _criar_serie(db, tenant_id):
    origem = ContaPagar(
        descricao="aluguel demonstracao",
        valor_original=Decimal("10000.00"),
        valor_final=Decimal("10000.00"),
        valor_pago=Decimal("0"),
        data_emissao=date(2026, 9, 25),
        data_vencimento=date(2026, 9, 25),
        status="pendente",
        eh_recorrente=True,
        tipo_recorrencia="mensal",
        user_id=1,
        tenant_id=tenant_id,
    )
    db.add(origem)
    db.flush()
    filha = ContaPagar(
        descricao="aluguel demonstracao (Recorrencia 10/2026)",
        valor_original=Decimal("10000.00"),
        valor_final=Decimal("10000.00"),
        valor_pago=Decimal("0"),
        data_emissao=date(2026, 10, 25),
        data_vencimento=date(2026, 10, 25),
        status="pendente",
        conta_recorrencia_origem_id=origem.id,
        user_id=1,
        tenant_id=tenant_id,
    )
    db.add(filha)
    db.flush()
    previsao = LancamentoManual(
        tipo="saida",
        valor=Decimal("10000.00"),
        descricao=filha.descricao,
        data_lancamento=filha.data_vencimento,
        status="previsto",
        gerado_automaticamente=True,
        observacoes=(
            f"Gerado automaticamente da conta a pagar #{filha.id} "
            f"(recorrencia #{origem.id})"
        ),
        user_id=1,
        tenant_id=tenant_id,
    )
    db.add(previsao)
    db.flush()
    return origem, filha, previsao


def test_excluir_origem_apaga_serie_e_previsao(db_session, tenant_context):
    tenant_id = uuid4()
    tenant_context(tenant_id)
    origem, filha, previsao = _criar_serie(db_session, tenant_id)
    ids = (origem.id, filha.id, previsao.id)

    resposta = excluir_conta_pagar(ids[0], db_session, (None, tenant_id))

    assert resposta["total"] == 2
    assert db_session.get(ContaPagar, ids[0]) is None
    assert db_session.get(ContaPagar, ids[1]) is None
    assert db_session.get(LancamentoManual, ids[2]) is None


def test_excluir_origem_preserva_serie_com_pagamento(db_session, tenant_context):
    tenant_id = uuid4()
    tenant_context(tenant_id)
    origem, filha, previsao = _criar_serie(db_session, tenant_id)
    filha.valor_pago = Decimal("10.00")
    db_session.flush()

    with pytest.raises(HTTPException) as erro:
        excluir_conta_pagar(origem.id, db_session, (None, tenant_id))

    assert erro.value.status_code == 400
    assert db_session.get(ContaPagar, origem.id) is not None
    assert db_session.get(ContaPagar, filha.id) is not None
    assert db_session.get(LancamentoManual, previsao.id) is not None


def test_exclusao_em_lote_exige_serie_completa(db_session, tenant_context):
    tenant_id = uuid4()
    tenant_context(tenant_id)
    origem, filha, previsao = _criar_serie(db_session, tenant_id)

    with pytest.raises(HTTPException) as erro:
        excluir_recorrencias_contas_pagar(
            ContaPagarRecorrenciaBulkDelete(ids=[origem.id]),
            db_session,
            (None, tenant_id),
        )
    assert erro.value.status_code == 400

    resposta = excluir_recorrencias_contas_pagar(
        ContaPagarRecorrenciaBulkDelete(ids=[origem.id, filha.id]),
        db_session,
        (None, tenant_id),
    )
    assert resposta["total"] == 2
    assert db_session.get(LancamentoManual, previsao.id) is None
