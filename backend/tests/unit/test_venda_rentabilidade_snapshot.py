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
