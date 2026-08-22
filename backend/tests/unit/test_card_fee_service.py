from collections import defaultdict, deque
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.financeiro_models import FormaPagamento
from app.operadoras_models import OperadoraCartao, OperadoraCartaoTaxa
from app.services.card_fee_service import (
    CardFeeConfigurationError,
    resolve_card_fee,
)


class _FakeQuery:
    def __init__(self, results):
        self.results = results

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.results.popleft() if self.results else None


class _FakeSession:
    def __init__(self, scripted):
        self.scripted = defaultdict(deque)
        for model, results in scripted.items():
            self.scripted[model].extend(results)

    def query(self, model):
        return _FakeQuery(self.scripted[model])


def _forma(**overrides):
    values = {
        "id": 10,
        "tipo": "cartao_credito",
        "tipo_cartao": "credito",
        "nome": "Cartao de credito",
        "taxa_percentual": Decimal("3.00"),
        "taxa_fixa": Decimal("0.00"),
        "taxas_por_parcela": None,
        "prazo_dias": 30,
        "operadora_id": None,
        "bandeira": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _operadora(**overrides):
    values = {
        "id": 7,
        "nome": "Stone",
        "max_parcelas": 12,
        "taxa_debito": None,
        "taxa_credito_vista": None,
        "taxa_credito_parcelado": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_resolve_regra_exata_e_calcula_snapshot_da_taxa():
    regra = SimpleNamespace(
        id=91,
        taxa_percentual=Decimal("2.4900"),
        taxa_fixa=Decimal("0.50"),
        prazo_recebimento_dias=30,
    )
    db = _FakeSession(
        {
            FormaPagamento: [_forma()],
            OperadoraCartao: [_operadora()],
            OperadoraCartaoTaxa: [regra],
        }
    )

    resultado = resolve_card_fee(
        db,
        tenant_id="tenant",
        valor=100,
        forma_pagamento_id=10,
        operadora_id=7,
        bandeira="Visa",
        modalidade="credito",
        parcelas=1,
    )

    assert resultado.regra_id == 91
    assert resultado.bandeira == "visa"
    assert resultado.taxa_percentual == Decimal("2.4900")
    assert resultado.valor_taxa == Decimal("2.99")
    assert resultado.valor_liquido == Decimal("97.01")
    assert resultado.data_recebimento_prevista >= date.today()


def test_bloqueia_combinacao_sem_taxa_quando_operadora_ja_tem_matriz():
    db = _FakeSession(
        {
            FormaPagamento: [_forma()],
            OperadoraCartao: [_operadora()],
            OperadoraCartaoTaxa: [None, None, SimpleNamespace(id=1)],
        }
    )

    with pytest.raises(CardFeeConfigurationError, match="Taxa nao cadastrada"):
        resolve_card_fee(
            db,
            tenant_id="tenant",
            valor=100,
            forma_pagamento_id=10,
            operadora_id=7,
            bandeira="Elo",
            modalidade="credito",
            parcelas=6,
        )


def test_mantem_compatibilidade_com_json_legado_numerico_ou_detalhado():
    forma = _forma(
        taxa_percentual=Decimal("1.00"),
        taxa_fixa=Decimal("0.20"),
        taxas_por_parcela='{"2": 2.5, "3": {"taxa_percentual": 3.1, "taxa_fixa": 0.40}}',
    )
    db = _FakeSession({FormaPagamento: [forma]})

    resultado = resolve_card_fee(
        db,
        tenant_id="tenant",
        valor=200,
        forma_pagamento_id=10,
        operadora_id=None,
        bandeira="Mastercard",
        modalidade="credito",
        parcelas=3,
    )

    assert resultado.fonte == "forma_pagamento_legada"
    assert resultado.taxa_percentual == Decimal("3.1")
    assert resultado.taxa_fixa == Decimal("0.40")
    assert resultado.valor_taxa == Decimal("6.60")
