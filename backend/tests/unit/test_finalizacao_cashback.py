"""Cashback quita o PDV junto ao pagamento monetario, sem entrar no caixa."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import Enum, Integer, MetaData

from app.caixa_models import MovimentacaoCaixa
from app.campaigns.cashback_wallet import get_cashback_wallet
from app.campaigns.models import (
    Campaign,
    CampaignEventQueue,
    CashbackSourceTypeEnum,
    CashbackTransaction,
)
from app.financeiro_models import LancamentoManual
from app.models import Cliente
from app.vendas_models import VendaPagamento
from tests.unit.test_finalizacao_resumo_cupom import (
    cupom,  # noqa: F401
    finalizar,
    preparar_venda,
)
from tests.unit.test_finalizacao_recebiveis_atomicidade import cenario  # noqa: F401


@pytest.fixture
def venda_cashback(request):
    caso = request.getfixturevalue("cupom")
    engine = caso.db.get_bind()
    if engine.dialect.name == "sqlite":
        # SQLite exige INTEGER para gerar IDs e nao possui clock_timestamp().
        # A carteira e o resgate continuam usando as consultas e gravacoes reais.
        connection = engine.raw_connection()
        connection.create_function(
            "clock_timestamp",
            0,
            lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"),
        )
        connection.close()
    for model in (Campaign, CampaignEventQueue, CashbackTransaction):
        tabela = model.__table__.to_metadata(MetaData())
        if engine.dialect.name == "sqlite":
            tabela.c.id.type = Integer()
        else:
            for coluna in tabela.columns:
                if isinstance(coluna.type, Enum):
                    coluna.type.create(engine, checkfirst=True)
        tabela.create(engine)

    preparar_venda(caso, Decimal("93.90"))
    cliente = caso.db.query(Cliente).filter_by(tenant_id=caso.tenant).one()
    caso.venda.cliente_id = cliente.id
    caso.db.add(
        CashbackTransaction(
            tenant_id=caso.tenant,
            customer_id=cliente.id,
            amount=Decimal("100.00"),
            source_type=CashbackSourceTypeEnum.manual,
            tx_type="credit",
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
    )
    caso.db.commit()
    return caso


def pix(valor):
    return {"forma_pagamento": "PIX", "forma_pagamento_id": 1, "valor": valor}


def cashback(valor):
    # Mesmo contrato do botao de cashback do modal: nao ha cadastro de forma.
    return {"forma_pagamento": "Cashback", "valor": valor}


@pytest.mark.parametrize("complemento", [False, True], ids=["misto", "complemento"])
def test_cashback_completa_venda_de_93_90_sem_pendencia(venda_cashback, complemento):
    caso = venda_cashback
    if complemento:
        parcial = finalizar(caso, [pix(90)])
        assert parcial["status"] == "baixa_parcial"
        assert parcial["status_pagamento"] == "parcial"
        assert parcial["valor_pago"] == 90
        assert parcial["valor_restante"] == 3.9
        pagamentos = [cashback(3.9)]
    else:
        pagamentos = [pix(90), cashback(3.9)]

    resposta = finalizar(caso, pagamentos)

    conferir_quitacao(caso, resposta, Decimal("3.90"), pagamentos_esperados=2)


def test_cashback_integral_quita_venda_sem_movimento_fisico(venda_cashback):
    caso = venda_cashback

    resposta = finalizar(caso, [cashback(93.9)])

    conferir_quitacao(caso, resposta, Decimal("93.90"), pagamentos_esperados=1)


def conferir_quitacao(caso, resposta, valor_cashback, *, pagamentos_esperados):
    assert resposta["status"] == "finalizada"
    assert resposta["status_pagamento"] == "pago"
    assert resposta["valor_pago"] == 93.9
    assert resposta["valor_restante"] == 0
    assert len(resposta["pagamentos"]) == pagamentos_esperados
    assert caso.db.query(VendaPagamento).count() == pagamentos_esperados
    [resgate] = (
        caso.db.query(CashbackTransaction)
        .filter_by(source_type=CashbackSourceTypeEnum.redemption)
        .all()
    )
    assert resgate.customer_id == caso.venda.cliente_id
    assert resgate.source_id == caso.venda.id
    assert resgate.amount == -valor_cashback
    assert (
        get_cashback_wallet(
            caso.db, tenant_id=caso.tenant, customer_id=caso.venda.cliente_id
        ).available
        == Decimal("100.00") - valor_cashback
    )
    assert caso.db.query(MovimentacaoCaixa).count() == 0
    [despesa] = (
        caso.db.query(LancamentoManual)
        .filter_by(documento=f"CASHBACK-{caso.venda.numero_venda}")
        .all()
    )
    assert despesa.valor == valor_cashback
    assert despesa.status == "realizado"
