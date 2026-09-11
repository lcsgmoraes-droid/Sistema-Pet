from datetime import date
from decimal import Decimal

from app.vendas.finalizacao_routes import _converter_pagamentos_request
from app.vendas.finalizacao_pagamentos import _montar_campos_venda_pagamento
from app.vendas.schemas import VendaPagamentoSchema
from app.vendas_models import VendaPagamento


def test_campos_pagamento_cartao_usam_prazo_resolvido_sem_duplicar_kwargs():
    data_prevista = date(2026, 8, 23)

    campos = _montar_campos_venda_pagamento(
        venda_id=1068348,
        tenant_id="tenant-aumigospet",
        pag_data={
            "forma_pagamento": "Cartao de debito",
            "valor": 55.0,
            "prazo_recebimento_dias": 99,
            "data_recebimento_prevista": date(2026, 12, 1),
        },
        forma_pagamento_id=7,
        numero_parcelas=1,
        bandeira="visa",
        operadora_id=3,
        taxa_aplicada={
            "modalidade_cartao": "debito",
            "taxa_cartao_regra_id": 12,
            "prazo_recebimento_dias": 1,
            "data_recebimento_prevista": data_prevista,
        },
    )

    assert campos["prazo_recebimento_dias"] == 1
    assert campos["data_recebimento_prevista"] == data_prevista
    assert campos["intervalo_crediario"] is None
    assert campos["modalidade_cartao"] == "debito"
    assert campos["taxa_cartao_regra_id"] == 12


def test_campos_pagamento_sem_taxa_preservam_prazo_informado():
    data_prevista = date(2026, 9, 1)

    campos = _montar_campos_venda_pagamento(
        venda_id=10,
        tenant_id="tenant-teste",
        pag_data={
            "forma_pagamento": "Crediario",
            "valor": 80.0,
            "prazo_recebimento_dias": 10,
            "data_recebimento_prevista": data_prevista,
            "intervalo_crediario": "mensal",
        },
        forma_pagamento_id=8,
        numero_parcelas=1,
        bandeira=None,
        operadora_id=None,
        taxa_aplicada={},
    )

    assert campos["prazo_recebimento_dias"] == 10
    assert campos["data_recebimento_prevista"] == data_prevista
    assert campos["intervalo_crediario"] == "mensal"


def test_campos_pagamento_em_dinheiro_preservam_valor_recebido_e_troco():
    campos = _montar_campos_venda_pagamento(
        venda_id=11,
        tenant_id="tenant-teste",
        pag_data={
            "forma_pagamento": "Dinheiro",
            "valor": 45.0,
            "valor_recebido": 50.0,
            "troco": 5.0,
        },
        forma_pagamento_id=1,
        numero_parcelas=1,
        bandeira=None,
        operadora_id=None,
        taxa_aplicada={},
    )

    assert campos["valor_recebido"] == 50.0
    assert campos["troco"] == 5.0


def test_rota_de_finalizacao_encaminha_valor_recebido_e_troco_ao_servico():
    [pagamento] = _converter_pagamentos_request(
        [
            VendaPagamentoSchema(
                forma_pagamento="Dinheiro",
                valor=45.0,
                valor_recebido=50.0,
                troco=5.0,
            )
        ]
    )

    assert pagamento["valor"] == 45.0
    assert pagamento["valor_recebido"] == 50.0
    assert pagamento["troco"] == 5.0


def test_pagamento_serializado_expoe_valor_recebido_e_troco():
    pagamento = VendaPagamento(
        forma_pagamento="Dinheiro",
        valor=Decimal("45.00"),
        valor_recebido=Decimal("50.00"),
        troco=Decimal("5.00"),
    )

    data = pagamento.to_dict()

    assert data["valor"] == 45.0
    assert data["valor_recebido"] == 50.0
    assert data["troco"] == 5.0
