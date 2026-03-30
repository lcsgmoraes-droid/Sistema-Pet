from types import SimpleNamespace
from unittest.mock import Mock

from app.integracao_bling_pedido_routes import (
    _confirmar_pedido,
    _normalizar_canal,
    _resumir_ultima_nf_do_pedido_bling,
    _resumir_ultima_nf_webhook,
    _resolver_canal_pedido,
    _serializar_pedido_bling,
    _situacao_codigo_bling,
)


def test_situacao_codigo_bling_prioriza_id():
    assert _situacao_codigo_bling({"id": 9, "valor": 1}) == 9


def test_situacao_codigo_bling_faz_fallback_para_valor():
    assert _situacao_codigo_bling({"valor": 5}) == 5


def test_normalizar_canal_marketplace():
    canal, label, origem = _normalizar_canal("Mercado Livre Full")

    assert canal == "mercado_livre"
    assert label == "Mercado Livre"
    assert origem == "Mercado Livre Full"


def test_resumir_ultima_nf_webhook_captura_valor_total_da_nota():
    resumo = _resumir_ultima_nf_webhook(
        {
            "id": "25428517969",
            "numero": "010984",
            "serie": "1",
            "dataEmissao": "2026-03-29",
            "situacao": {"valor": 5, "descricao": "Autorizada"},
            "chaveAcesso": "CHAVE-XYZ",
            "valorTotalNf": 166.90,
        }
    )

    assert resumo["id"] == "25428517969"
    assert resumo["numero"] == "010984"
    assert resumo["data_emissao"] == "2026-03-29"
    assert resumo["situacao"] == "Autorizada"
    assert resumo["situacao_codigo"] == 5
    assert resumo["valor_total"] == 166.90


def test_resumir_ultima_nf_do_pedido_bling_enriquece_detalhes_via_api(monkeypatch):
    class FakeBling:
        def consultar_nfe(self, nf_id):
            assert nf_id == 25431833504
            return {
                "id": 25431833504,
                "numero": "010985",
                "serie": 2,
                "situacao": 5,
                "valorNota": 440.13,
                "chaveAcesso": "CHAVE-10985",
            }

        def consultar_nfce(self, nf_id):
            raise AssertionError("nao deveria consultar NFC-e quando NFe ja respondeu")

    monkeypatch.setattr("app.bling_integration.BlingAPI", lambda: FakeBling())

    resumo = _resumir_ultima_nf_do_pedido_bling({"notaFiscal": {"id": "25431833504"}})

    assert resumo["id"] == "25431833504"
    assert resumo["numero"] == "010985"
    assert resumo["valor_total"] == 440.13
    assert resumo["chave"] == "CHAVE-10985"


def test_resolver_canal_pedido_prioriza_loja_id_quando_canal_salvo_era_bling():
    canal, label, origem = _resolver_canal_pedido(
        {
            "pedido": {
                "canal": "Bling",
                "loja": {"id": 205367939},
                "numeroPedidoLoja": "260329CJYQJRA2",
            }
        },
        "bling",
    )

    assert canal == "shopee"
    assert label == "Shopee"
    assert origem == "shopee"


def test_resolver_canal_pedido_inferido_pelo_numero_loja_virtual():
    canal, label, origem = _resolver_canal_pedido(
        {
            "pedido": {
                "canal": "Bling",
                "numeroPedidoLoja": "2000015737461914",
            }
        },
        "bling",
    )

    assert canal == "mercado_livre"
    assert label == "Mercado Livre"
    assert origem == "mercado_livre"


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


def test_confirmar_pedido_so_marca_item_vendido_apos_baixa(monkeypatch):
    db = Mock()
    pedido = SimpleNamespace(
        id=10,
        tenant_id="tenant-1",
        pedido_bling_id="987",
        status="aberto",
        confirmado_em=None,
    )
    item = SimpleNamespace(sku="KIT-1", quantidade=1, vendido_em=None)
    confirmados = []

    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes._baixar_item_pedido",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes.EstoqueReservaService.confirmar_venda",
        lambda db_arg, item_arg: (confirmados.append(item_arg.sku), setattr(item_arg, "vendido_em", "ok")),
    )
    monkeypatch.setattr("app.integracao_bling_pedido_routes.registrar_evento", lambda **kwargs: None)
    monkeypatch.setattr("app.integracao_bling_pedido_routes.abrir_incidente", lambda **kwargs: None)

    erros = _confirmar_pedido(
        db=db,
        pedido=pedido,
        itens=[item],
        motivo="teste",
        observacao="teste",
        aplicar_baixa_estoque=True,
    )

    assert erros == []
    assert confirmados == ["KIT-1"]
    assert item.vendido_em == "ok"


def test_confirmar_pedido_mantem_reserva_quando_baixa_falha(monkeypatch):
    db = Mock()
    pedido = SimpleNamespace(
        id=10,
        tenant_id="tenant-1",
        pedido_bling_id="987",
        status="aberto",
        confirmado_em=None,
    )
    item = SimpleNamespace(sku="KIT-1", quantidade=1, vendido_em=None)
    confirmados = []

    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes._baixar_item_pedido",
        lambda **kwargs: "falha baixa",
    )
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes.EstoqueReservaService.confirmar_venda",
        lambda db_arg, item_arg: confirmados.append(item_arg.sku),
    )
    monkeypatch.setattr("app.integracao_bling_pedido_routes.registrar_evento", lambda **kwargs: None)
    monkeypatch.setattr("app.integracao_bling_pedido_routes.abrir_incidente", lambda **kwargs: None)

    erros = _confirmar_pedido(
        db=db,
        pedido=pedido,
        itens=[item],
        motivo="teste",
        observacao="teste",
        aplicar_baixa_estoque=True,
    )

    assert erros == ["falha baixa"]
    assert confirmados == []
    assert item.vendido_em is None


def test_confirmar_pedido_sem_nf_nao_baixa_estoque_nem_marca_item(monkeypatch):
    db = Mock()
    pedido = SimpleNamespace(
        id=10,
        tenant_id="tenant-1",
        pedido_bling_id="987",
        status="aberto",
        confirmado_em=None,
    )
    item = SimpleNamespace(sku="KIT-1", quantidade=1, vendido_em=None)
    baixas = []
    confirmados = []
    eventos = []

    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes._baixar_item_pedido",
        lambda **kwargs: baixas.append(kwargs),
    )
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes.EstoqueReservaService.confirmar_venda",
        lambda db_arg, item_arg: confirmados.append(item_arg.sku),
    )
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes.registrar_evento",
        lambda **kwargs: eventos.append(kwargs),
    )

    erros = _confirmar_pedido(
        db=db,
        pedido=pedido,
        itens=[item],
        motivo="teste",
        observacao="teste",
    )

    assert erros == []
    assert baixas == []
    assert confirmados == []
    assert item.vendido_em is None
    assert eventos[0]["payload"]["baixa_estoque_status"] == "nf_pendente"
