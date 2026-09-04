from types import SimpleNamespace

from app.vendas.finalizacao_pagamentos import consumir_cupom_finalizacao


def test_finalizacao_consumo_cupons_em_sequencia(monkeypatch):
    chamadas = []

    def consumir(_db, **kwargs):
        chamadas.append(kwargs)
        desconto = 10.0 if kwargs["code"] == "PRIMEIRO" else 5.0
        return {"coupon_code": kwargs["code"], "discount_applied": desconto}

    monkeypatch.setattr(
        "app.campaigns.coupon_service.consume_coupon_redemption", consumir
    )
    venda = SimpleNamespace(
        id=7,
        cliente_id=11,
        total=85.0,
        cupom_code=None,
        cupom_discount_applied=None,
    )

    resultado = consumir_cupom_finalizacao(
        venda=venda,
        cupom_code="primeiro,segundo",
        cupom_discount_applied=15.0,
        tenant_id="tenant-1",
        db=object(),
    )

    assert [chamada["venda_total"] for chamada in chamadas] == [100.0, 90.0]
    assert venda.cupom_code == "PRIMEIRO,SEGUNDO"
    assert venda.cupom_discount_applied == 15.0
    assert len(resultado["redemptions"]) == 2
