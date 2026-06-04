from types import SimpleNamespace

from app.services.venda_rentabilidade_snapshot_service import (
    SNAPSHOT_VERSION,
    build_venda_rentabilidade_snapshot,
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
