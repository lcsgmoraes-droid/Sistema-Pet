from types import SimpleNamespace
from unittest.mock import Mock

from app.integracao_bling_pedido_routes import (
    _confirmar_pedido,
    _montar_payload_pedido,
    _normalizar_canal,
    _resumir_ultima_nf_do_pedido_bling,
    _resumir_ultima_nf_webhook,
    _resolver_canal_pedido,
    _serializar_pedido_bling,
    _situacao_codigo_bling,
)
from app.services.pedido_integrado_consolidation_service import (
    escolher_pedido_canonico,
    marcar_payload_como_mesclado,
    numero_pedido_loja_do_payload,
    pedido_esta_mesclado,
    registrar_alias_bling_no_payload,
    ultima_nf_do_payload,
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


def test_montar_payload_pedido_preserva_ultima_nf_mais_recente():
    payload = _montar_payload_pedido(
        webhook_data={"pedido": {"numero": "11733"}},
        pedido_completo={"numero": "11733"},
        payload_atual={
            "ultima_nf": {
                "id": "25441651448",
                "numero": "011089",
                "serie": "2",
                "situacao": "Autorizada",
                "data_emissao": "2026-03-30 19:28:21",
            }
        },
        ultima_nf={
            "id": "25441651001",
            "numero": "011088",
            "serie": "2",
            "situacao": "Autorizada",
            "data_emissao": "2026-03-30 19:28:16",
        },
    )

    assert payload["ultima_nf"]["id"] == "25441651448"
    assert payload["ultima_nf"]["numero"] == "011089"


def test_montar_payload_pedido_substitui_placeholder_ultima_nf_por_nf_real():
    payload = _montar_payload_pedido(
        webhook_data={"pedido": {"numero": "12168"}},
        pedido_completo={"numero": "12168", "notaFiscal": {"id": "25513413824"}},
        payload_atual={
            "ultima_nf": {
                "id": "0",
                "numero": None,
                "serie": None,
                "situacao": None,
                "data_emissao": None,
            }
        },
        ultima_nf={"id": "25513413824"},
    )

    assert payload["ultima_nf"]["id"] == "25513413824"


def test_numero_pedido_loja_do_payload_prioriza_pedido_e_faz_fallback():
    assert numero_pedido_loja_do_payload({"pedido": {"numeroPedidoLoja": "LOJA-1"}}) == "LOJA-1"
    assert numero_pedido_loja_do_payload({"webhook": {"numeroLoja": "LOJA-2"}}) == "LOJA-2"


def test_ultima_nf_do_payload_ignora_placeholder_e_faz_fallback_para_nota_fiscal_do_pedido():
    payload = {
        "pedido": {"notaFiscal": {"id": "25513413824"}},
        "ultima_nf": {
            "id": "0",
            "numero": None,
            "serie": None,
            "situacao": None,
            "data_emissao": None,
        },
    }

    assert ultima_nf_do_payload(payload)["id"] == "25513413824"


def test_registrar_alias_bling_no_payload_evita_duplicidade():
    payload = registrar_alias_bling_no_payload(
        {"pedido": {"numeroPedidoLoja": "260330GDQVHGXX"}},
        pedido_bling_id="25439737683",
        pedido_bling_numero="11680",
        numero_pedido_loja="260330GDQVHGXX",
        loja_id="205367939",
    )
    payload = registrar_alias_bling_no_payload(
        payload,
        pedido_bling_id="25439737683",
        pedido_bling_numero="11680",
        numero_pedido_loja="260330GDQVHGXX",
        loja_id="205367939",
    )

    assert len(payload["pedidos_bling_aliases"]) == 1
    assert payload["pedidos_bling_aliases"][0]["pedido_bling_id"] == "25439737683"


def test_marcar_payload_como_mesclado_sinaliza_canonico():
    pedido_canonico = SimpleNamespace(id=10, pedido_bling_id="25438349686", pedido_bling_numero="11629")

    payload = marcar_payload_como_mesclado(
        {"pedido": {"numeroPedidoLoja": "260330GDQVHGXX"}},
        pedido_canonico=pedido_canonico,
        numero_pedido_loja="260330GDQVHGXX",
        loja_id="205367939",
    )

    assert pedido_esta_mesclado(payload) is True
    assert payload["pedido_mesclado"]["pedido_canonico_id"] == 10


def test_escolher_pedido_canonico_prefere_pedido_com_nf():
    sem_nf = SimpleNamespace(
        id=20,
        status="confirmado",
        created_at=None,
        criado_em=None,
        payload={"pedido": {"numeroPedidoLoja": "260330GDQVHGXX"}},
    )
    com_nf = SimpleNamespace(
        id=10,
        status="aberto",
        created_at=None,
        criado_em=None,
        payload={
            "pedido": {"numeroPedidoLoja": "260330GDQVHGXX"},
            "ultima_nf": {"id": "25441651448", "numero": "011089"},
        },
    )

    escolhido = escolher_pedido_canonico([sem_nf, com_nf])

    assert escolhido.id == 10


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


def test_serializar_pedido_bling_ignora_placeholder_ultima_nf():
    pedido = SimpleNamespace(
        id=11,
        pedido_bling_id="25513398915",
        pedido_bling_numero="12168",
        canal="shopee",
        status="confirmado",
        criado_em=None,
        expira_em=None,
        confirmado_em=None,
        cancelado_em=None,
        payload={
            "pedido": {
                "numero": "12168",
                "numeroLoja": "260408AF627Y4R",
                "notaFiscal": {"id": "25513413824"},
                "itens": [],
            },
            "ultima_nf": {
                "id": "0",
                "numero": None,
                "serie": None,
                "situacao": None,
                "data_emissao": None,
            },
        },
    )

    serializado = _serializar_pedido_bling(pedido, [])

    assert serializado["nota_fiscal"]["id"] == "25513413824"


def test_serializar_pedido_bling_expoe_contexto_duplicidade_e_acoes():
    pedido = SimpleNamespace(
        id=20,
        pedido_bling_id="25439737683",
        pedido_bling_numero="11680",
        canal="shopee",
        status="confirmado",
        criado_em=None,
        expira_em=None,
        confirmado_em=None,
        cancelado_em=None,
        payload={"pedido": {"numeroPedidoLoja": "260330GDQVHGXX", "itens": []}},
    )

    serializado = _serializar_pedido_bling(
        pedido,
        [],
        duplicidade={
            "tem_duplicados": True,
            "pedido_atual_eh_canonico": True,
            "pedidos_seguro_ids": [21],
            "pedidos_bloqueados_ids": [],
            "bloqueios": [],
            "pedidos_duplicados": [{"id": 21, "pedido_bling_numero": "11681"}],
            "requer_revisao_manual": False,
        },
    )

    assert serializado["duplicidade"]["tem_duplicados"] is True
    assert serializado["acoes_disponiveis"]["pode_consolidar_duplicidade"] is True
    assert serializado["acoes_disponiveis"]["pode_reconciliar_fluxo"] is True


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
