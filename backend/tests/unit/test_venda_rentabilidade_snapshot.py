from copy import deepcopy
from types import SimpleNamespace

from app.dre_canais.base import _snapshot_pronto
from app.services.venda_rentabilidade_snapshot_service import (
    SNAPSHOT_VERSION,
    ajustar_snapshot_taxa_mista,
    build_venda_rentabilidade_snapshot,
    get_or_build_venda_rentabilidade_snapshot,
)


def test_snapshot_reclassifica_desconto_de_cupom_como_custo_campanha():
    venda = SimpleNamespace(
        id=123,
        numero_venda="202605150038",
        status="finalizada",
        data_venda=None,
        cliente=SimpleNamespace(nome="Cliente QA"),
        subtotal=79.40,
        desconto_valor=25.00,
        taxa_entrega=0,
        valor_taxa_entregador=0,
        tem_entrega=False,
        entregador_id=None,
        cupom_code="FIDE-TESTE",
        cupom_discount_applied=25.00,
        itens=[
            SimpleNamespace(
                produto_id=10,
                quantidade=1,
                preco_unitario=104.40,
                produto=SimpleNamespace(nome="Produto QA", preco_custo=50.00),
            )
        ],
        pagamentos=[],
    )

    snapshot = build_venda_rentabilidade_snapshot(
        venda,
        db=SimpleNamespace(query=lambda *_args, **_kwargs: None),
        tenant_id="tenant-qa",
        impostos_percentual=0,
        formas_pagamento_map={},
        custo_campanha=25.00,
        cupom_desconto=25.00,
        comissao_total=0,
        estoque_custos_por_produto={},
    )

    assert snapshot["snapshot_version"] == SNAPSHOT_VERSION
    assert snapshot["venda_bruta"] == 104.40
    assert snapshot["desconto"] == 0
    assert snapshot["cupom_code"] == "FIDE-TESTE"
    assert snapshot["cupom_desconto"] == 25.00
    assert snapshot["custo_campanha"] == 25.00
    assert snapshot["itens"][0]["desconto"] == 0
    assert snapshot["itens"][0]["campanha"] == 25.00


def test_snapshot_mantem_desconto_manual_sem_cupom_como_desconto():
    venda = SimpleNamespace(
        id=124,
        numero_venda="202605150039",
        status="finalizada",
        data_venda=None,
        cliente=SimpleNamespace(nome="Cliente QA"),
        subtotal=79.40,
        desconto_valor=25.00,
        taxa_entrega=0,
        valor_taxa_entregador=0,
        tem_entrega=False,
        entregador_id=None,
        cupom_code=None,
        cupom_discount_applied=None,
        itens=[
            SimpleNamespace(
                produto_id=10,
                quantidade=1,
                preco_unitario=104.40,
                produto=SimpleNamespace(nome="Produto QA", preco_custo=50.00),
            )
        ],
        pagamentos=[],
    )

    snapshot = build_venda_rentabilidade_snapshot(
        venda,
        db=SimpleNamespace(query=lambda *_args, **_kwargs: None),
        tenant_id="tenant-qa",
        impostos_percentual=0,
        formas_pagamento_map={},
        custo_campanha=0,
        cupom_desconto=0,
        comissao_total=0,
        estoque_custos_por_produto={},
    )

    assert snapshot["desconto"] == 25.00
    assert snapshot["cupom_code"] is None
    assert snapshot["cupom_desconto"] == 0
    assert snapshot["custo_campanha"] == 0
    assert snapshot["itens"][0]["desconto"] == 25.00
    assert snapshot["itens"][0]["campanha"] == 0


def test_snapshot_usa_taxa_real_do_gateway_quando_pagamento_online_tem_dados_mp():
    venda = SimpleNamespace(
        id=125,
        numero_venda="202606020502",
        status="finalizada",
        data_venda=None,
        cliente=SimpleNamespace(nome="Cliente App"),
        subtotal=3.98,
        desconto_valor=0,
        taxa_entrega=0,
        valor_taxa_entregador=0,
        tem_entrega=False,
        entregador_id=None,
        cupom_code=None,
        cupom_discount_applied=None,
        itens=[
            SimpleNamespace(
                produto_id=10,
                quantidade=2,
                preco_unitario=1.99,
                produto=SimpleNamespace(nome="Produto QA", preco_custo=1.20),
            )
        ],
        pagamentos=[
            SimpleNamespace(
                forma_pagamento="PIX",
                valor=3.98,
                numero_parcelas=1,
                gateway_provider="mercadopago",
                gateway_payment_id="1387729134",
                gateway_fee_amount=0.23,
                gateway_net_amount=3.75,
            )
        ],
    )

    snapshot = build_venda_rentabilidade_snapshot(
        venda,
        db=SimpleNamespace(query=lambda *_args, **_kwargs: None),
        tenant_id="tenant-qa",
        impostos_percentual=0,
        formas_pagamento_map={"pix": SimpleNamespace(taxa_percentual=0)},
        custo_campanha=0,
        cupom_desconto=0,
        comissao_total=0,
        estoque_custos_por_produto={},
    )

    assert snapshot["taxa_cartao"] == 0.23
    assert snapshot["taxa_gateway"] == 0.23
    assert snapshot["valor_liquido_gateway"] == 3.75
    assert snapshot["gateway_provider"] == "mercadopago"
    assert snapshot["gateway_payment_ids"] == ["1387729134"]
    assert snapshot["venda_liquida"] == 3.75
    assert snapshot["itens"][0]["taxa_cartao"] == 0.23


def test_snapshot_soma_taxas_de_gateway_e_pagamentos_locais_na_mesma_venda():
    venda = SimpleNamespace(
        id=127,
        numero_venda="202610050001",
        status="finalizada",
        data_venda=None,
        cliente=SimpleNamespace(nome="Cliente QA"),
        subtotal=100,
        desconto_valor=0,
        taxa_entrega=0,
        valor_taxa_entregador=0,
        tem_entrega=False,
        entregador_id=None,
        cupom_code=None,
        cupom_discount_applied=None,
        itens=[
            SimpleNamespace(
                produto_id=10,
                quantidade=1,
                preco_unitario=100,
                produto=SimpleNamespace(nome="Produto QA", preco_custo=0),
            )
        ],
        pagamentos=[
            SimpleNamespace(
                forma_pagamento="pix",
                valor=40,
                gateway_provider="mercadopago",
                gateway_fee_amount=1,
                valor_taxa_prevista=9,
            ),
            SimpleNamespace(
                forma_pagamento="cartao_credito",
                valor=30,
                valor_taxa_prevista=2,
            ),
            SimpleNamespace(forma_pagamento="cartao_debito", valor=20),
            SimpleNamespace(forma_pagamento="dinheiro", valor=10),
        ],
    )

    snapshot = build_venda_rentabilidade_snapshot(
        venda,
        db=SimpleNamespace(query=lambda *_args, **_kwargs: None),
        tenant_id="tenant-qa",
        impostos_percentual=0,
        formas_pagamento_map={
            "cartao_credito": SimpleNamespace(taxa_percentual=99, taxa_fixa=10),
            "cartao_debito": SimpleNamespace(taxa_percentual=1, taxa_fixa=0),
        },
        custo_campanha=0,
        cupom_desconto=0,
        comissao_total=0,
        estoque_custos_por_produto={},
    )

    assert snapshot["taxa_gateway"] == 1
    assert snapshot["taxa_cartao"] == 3.2  # gateway 1 + credito 2 + debito 0.2
    assert snapshot["venda_liquida"] == 96.8
    assert snapshot["itens"][0]["taxa_cartao"] == 3.2


def test_snapshot_historico_misto_corrige_so_taxa_e_totais_derivados_uma_vez():
    antigo = {
        "snapshot_version": SNAPSHOT_VERSION,
        "taxa_gateway": 1,
        "taxa_cartao": 1,
        "venda_bruta": 100,
        "venda_liquida": 79,
        "lucro": 49,
        "custo_produtos": 30,
        "imposto": 10,
        "desconto": 5,
        "itens": [
            {
                "venda_bruta": 100,
                "taxa_cartao": 1,
                "valor_liquido": 79,
                "lucro": 49,
                "custo_total": 30,
                "quantidade": 1,
            }
        ],
    }
    original = deepcopy(antigo)
    venda = SimpleNamespace(
        status="finalizada",
        rentabilidade_snapshot=antigo,
        pagamentos=[
            SimpleNamespace(gateway_provider="mercadopago", gateway_fee_amount=1),
            SimpleNamespace(valor_taxa_prevista=2),
        ],
    )

    corrigido = _snapshot_pronto(venda)
    assert corrigido["taxa_cartao"] == 3
    assert corrigido["venda_liquida"] == 77
    assert corrigido["lucro"] == 47
    assert corrigido["itens"][0]["taxa_cartao"] == 3
    assert corrigido["itens"][0]["lucro"] == 47
    assert corrigido["imposto"] == antigo["imposto"]
    assert corrigido["desconto"] == antigo["desconto"]
    assert corrigido["custo_produtos"] == antigo["custo_produtos"]
    assert antigo == original
    assert ajustar_snapshot_taxa_mista(venda, corrigido) is corrigido
    assert _snapshot_pronto(venda) == corrigido
    assert (
        get_or_build_venda_rentabilidade_snapshot(venda, db=None, tenant_id="tenant-qa")
        == corrigido
    )


def test_snapshot_preserva_taxa_aplicada_na_venda_mesmo_se_cadastro_mudar():
    venda = SimpleNamespace(
        id=126,
        numero_venda="202608210001",
        status="finalizada",
        data_venda=None,
        cliente=SimpleNamespace(nome="Cliente Loja"),
        subtotal=100,
        desconto_valor=0,
        taxa_entrega=0,
        valor_taxa_entregador=0,
        tem_entrega=False,
        entregador_id=None,
        cupom_code=None,
        cupom_discount_applied=None,
        itens=[
            SimpleNamespace(
                produto_id=10,
                quantidade=1,
                preco_unitario=100,
                produto=SimpleNamespace(nome="Produto QA", preco_custo=50),
            )
        ],
        pagamentos=[
            SimpleNamespace(
                forma_pagamento="cartao_credito",
                valor=100,
                numero_parcelas=1,
                valor_taxa_prevista=2.99,
                gateway_provider=None,
            )
        ],
    )

    snapshot = build_venda_rentabilidade_snapshot(
        venda,
        db=SimpleNamespace(query=lambda *_args, **_kwargs: None),
        tenant_id="tenant-qa",
        impostos_percentual=0,
        formas_pagamento_map={
            "cartao_credito": SimpleNamespace(taxa_percentual=99, taxa_fixa=10)
        },
        custo_campanha=0,
        cupom_desconto=0,
        comissao_total=0,
        estoque_custos_por_produto={},
    )

    assert snapshot["taxa_cartao"] == 2.99
    assert snapshot["venda_liquida"] == 97.01
