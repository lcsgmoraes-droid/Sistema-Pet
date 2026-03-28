from types import SimpleNamespace

from app.integracao_bling_pedido_routes import (
    _normalizar_canal,
    _serializar_pedido_bling,
    _situacao_codigo_bling,
)


def test_situacao_codigo_bling_prioriza_valor():
    assert _situacao_codigo_bling({"id": 5, "valor": 9}) == 9


def test_normalizar_canal_marketplace():
    canal, label, origem = _normalizar_canal("Mercado Livre Full")

    assert canal == "mercado_livre"
    assert label == "Mercado Livre"
    assert origem == "Mercado Livre Full"


def test_serializar_pedido_bling_expoe_campos_enriquecidos():
    pedido = SimpleNamespace(
        id=10,
        pedido_bling_id="987",
        pedido_bling_numero="12345",
        canal="online",
        status="aberto",
        criado_em=None,
        expira_em=None,
        confirmado_em=None,
        cancelado_em=None,
        payload={
            "pedido": {
                "numero": "12345",
                "numeroPedidoLoja": "LOJA-999",
                "numeroPedidoCanalVenda": "ML-ABC",
                "loja": {"id": 1, "nome": "Mercado Livre"},
                "contato": {
                    "nome": "Livia",
                    "numeroDocumento": "12345678900",
                    "email": "livia@email.com",
                    "telefone": "11999999999",
                },
                "total": 439.30,
                "desconto": 10,
                "transporte": {"frete": 20},
                "situacao": {"valor": 9, "descricao": "Atendido"},
                "itens": [
                    {
                        "codigo": "SKU-1",
                        "descricao": "Produto 1",
                        "quantidade": 2,
                        "valor": 15.5,
                        "total": 31.0,
                    }
                ],
            },
            "ultima_nf": {
                "id": "NF-1",
                "numero": "10971",
                "serie": "1",
                "situacao": "Autorizada",
                "chave": "CHAVE123",
            },
        },
    )
    itens = [
        SimpleNamespace(
            id=1,
            sku="SKU-1",
            descricao="Produto 1",
            quantidade=2,
            reservado_em=None,
            liberado_em=None,
            vendido_em=None,
        )
    ]

    serializado = _serializar_pedido_bling(pedido, itens)

    assert serializado["canal"] == "mercado_livre"
    assert serializado["canal_label"] == "Mercado Livre"
    assert serializado["numero_pedido_loja"] == "LOJA-999"
    assert serializado["numero_pedido_canal"] == "ML-ABC"
    assert serializado["cliente"]["nome"] == "Livia"
    assert serializado["financeiro"]["total"] == 439.30
    assert serializado["nota_fiscal"]["numero"] == "10971"
    assert serializado["itens"][0]["valor_unitario"] == 15.5
