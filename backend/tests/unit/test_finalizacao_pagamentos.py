from datetime import date

from app.vendas.finalizacao_pagamentos import _montar_campos_venda_pagamento


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
        },
        forma_pagamento_id=8,
        numero_parcelas=1,
        bandeira=None,
        operadora_id=None,
        taxa_aplicada={},
    )

    assert campos["prazo_recebimento_dias"] == 10
    assert campos["data_recebimento_prevista"] == data_prevista
