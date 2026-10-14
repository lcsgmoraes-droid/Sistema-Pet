"""Aceite HTTP dos descontos por origem, somente na homologação fictícia local."""

from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4

import pytest

from tests import test_plano_basico_e2e as jornada_basica
from tests.test_beneficios_devolucao_local_e2e import (
    _cliente,
    _finalizar,
    _get,
    _local_com_caixa_aberto,
    _produto,
)

api = jornada_basica.api
e2e_config = jornada_basica.e2e_config
pytestmark = pytest.mark.e2e_long


@pytest.fixture(scope="module", autouse=True)
def somente_local_antes_da_autenticacao(e2e_config):
    assert urlparse(e2e_config.base_url).hostname in {"localhost", "127.0.0.1"}


def _item(produto, desconto=0, quantidade=1, preco=100, item_id=None):
    result = {
        "tipo": "produto",
        "produto_id": produto["id"],
        "quantidade": quantidade,
        "preco_unitario": preco,
        "desconto_item": desconto,
        # O servidor deve recalcular, sem confiar no subtotal enviado pelo PDV.
        "subtotal": 9999,
    }
    if item_id:
        result["item_id"] = item_id
    return result


def _dados(cliente, produtos, prefix, global_valor=0, cupom=None):
    return {
        "cliente_id": cliente["id"],
        "itens": [_item(produtos[0], 20), _item(produtos[1])],
        "desconto_venda_valor": global_valor,
        "desconto_valor": 9876,  # Agregado também precisa ser recalculado.
        "cupom_code": cupom["code"] if cupom else None,
        "cupom_discount_applied": 5 if cupom else 0,
        "observacoes": prefix,
        "tem_entrega": False,
    }


def _conferir_venda(venda, produtos, global_valor, cupom_valor, total, subtotal=180):
    assert venda["desconto_origem_legado"] is False
    assert venda["subtotal"] == subtotal
    assert venda["desconto_itens_valor"] == 20
    assert venda["desconto_venda_valor"] == global_valor
    assert venda["cupom_discount_applied"] == cupom_valor
    assert venda["desconto_valor"] == 20 + global_valor + cupom_valor
    assert venda["total"] == total
    itens = {i["produto_id"]: i for i in venda["itens"]}
    assert itens[produtos[0]["id"]]["desconto_item"] == 20
    assert itens[produtos[1]["id"]]["desconto_item"] == 0
    return itens


def _conferir_financeiro(api, venda, produtos, global_valor, cupom_valor):
    analise = api.expect(
        "POST",
        "/formas-pagamento/analisar-venda",
        {200},
        "desconto.analise_pdv",
        json={
            "items": [
                {
                    "produto_id": item["produto_id"],
                    "quantidade": item["quantidade"],
                    "preco_venda": item["preco_unitario"],
                    "desconto_item": item["desconto_item"],
                }
                for item in venda["itens"]
            ],
            "desconto": 9876,
            "desconto_venda_valor": global_valor,
            "cupom_discount_applied": cupom_valor,
            "taxa_entrega": venda.get("taxa_entrega", 0),
        },
    ).json()["composicao"]
    assert analise["desconto_itens_valor"] == 20
    assert analise["desconto_venda_valor"] == global_valor
    assert analise["cupom_discount_applied"] == cupom_valor
    assert analise["desconto"] == 20 + global_valor + cupom_valor
    assert analise["subtotal"] == venda["total"]
    dia = venda["data_venda"][:10]
    relatorio = _get(api, "/relatorios/vendas/relatorio", data_inicio=dia, data_fim=dia)
    registro = next(v for v in relatorio["lista_vendas"] if v["id"] == venda["id"])
    assert registro["desconto_itens_valor"] == 20
    assert registro["desconto_venda_valor"] == global_valor
    assert registro["cupom_discount_applied"] == cupom_valor
    assert registro["desconto"] == 20 + global_valor
    linhas = {i["produto_id"]: i for i in registro["itens"]}
    assert linhas[produtos[0]["id"]]["desconto_item"] == 20
    assert linhas[produtos[1]["id"]]["desconto_item"] == 0
    assert (
        sum(Decimal(str(i["desconto_venda"])) for i in linhas.values()) == global_valor
    )
    assert (
        sum(Decimal(str(i["cupom_desconto"])) for i in linhas.values()) == cupom_valor
    )
    assert (
        sum(Decimal(str(i["desconto"])) for i in linhas.values()) == 20 + global_valor
    )
    return registro


def test_desconto_do_produto_fica_na_linha_financeira_e_na_devolucao(api):
    _local_com_caixa_aberto(api)
    prefix = "E2E-DESCONTO-ITEM-" + uuid4().hex[:8]
    cliente = _cliente(api, prefix)
    produtos = [_produto(api, prefix + suffix, preco=100) for suffix in ("-A", "-B")]
    venda = api.expect(
        "POST",
        "/vendas",
        {200, 201},
        "desconto.criar",
        json=_dados(cliente, produtos, prefix),
    ).json()
    _conferir_venda(venda, produtos, 0, 0, 180)
    venda = _finalizar(api, venda["id"], [{"forma_pagamento": "PIX", "valor": 180}])
    itens = _conferir_venda(venda, produtos, 0, 0, 180)
    financeiro = _conferir_financeiro(api, venda, produtos, 0, 0)
    linhas = {i["produto_id"]: i for i in financeiro["itens"]}
    assert linhas[produtos[0]["id"]]["desconto"] == 20
    assert linhas[produtos[1]["id"]]["desconto"] == 0
    for produto, valor in zip(produtos, (80, 100)):
        previa = api.expect(
            "POST",
            f"/vendas/{venda['id']}/devolucao/previa",
            {200},
            "desconto.devolucao_liquida_da_linha",
            json={
                "itens": [
                    {
                        "item_id": itens[produto["id"]]["id"],
                        "produto_id": produto["id"],
                        "quantidade": 1,
                    }
                ],
                "motivo": "Aceite fictício da identidade do desconto de produto.",
                "gerar_credito": True,
                "chave_operacao": str(uuid4()),
            },
        ).json()
        assert previa["valor_total_devolucao"] == valor
    print(
        f"DESCONTO_ITEM venda={venda['id']} numero={venda['numero_venda']} cliente={cliente['id']} bruto=200 desconto_A=20 desconto_B=0 total=180 devolucoes=80,100"
    )


def test_produto_global_cupom_separados_ao_salvar_finalizar_e_reabrir(api):
    caixa = _local_com_caixa_aberto(api)
    prefix = "E2E-DESCONTOS-ORIGEM-" + uuid4().hex[:8]
    cliente = _cliente(api, prefix)
    produtos = [_produto(api, prefix + suffix, preco=100) for suffix in ("-A", "-B")]
    cupom = api.expect(
        "POST",
        "/campanhas/cupons/manual",
        {200, 201},
        "desconto.cupom_exclusivo",
        json={
            "coupon_type": "fixed",
            "discount_value": 5,
            "channel": "pdv",
            "customer_id": cliente["id"],
            "motivo": prefix,
        },
    ).json()
    dados = _dados(cliente, produtos, prefix, global_valor=10, cupom=cupom)
    venda = api.expect(
        "POST", "/vendas", {200, 201}, "desconto.tres_origens", json=dados
    ).json()
    _conferir_venda(venda, produtos, 10, 5, 165)
    # Remover e recolocar cupom não pode apagar desconto de A nem o global.
    for ativo in (False, True):
        itens = {
            i["produto_id"]: i for i in _get(api, f"/vendas/{venda['id']}")["itens"]
        }
        dados = _dados(
            cliente, produtos, prefix, global_valor=10, cupom=cupom if ativo else None
        )
        for item in dados["itens"]:
            item["item_id"] = itens[item["produto_id"]]["id"]
        api.expect(
            "PUT",
            f"/vendas/{venda['id']}",
            {200},
            "desconto.cupom_independente",
            json=dados,
        )
        _conferir_venda(
            _get(api, f"/vendas/{venda['id']}"),
            produtos,
            10,
            5 if ativo else 0,
            165 if ativo else 170,
        )
    venda = _finalizar(api, venda["id"], [{"forma_pagamento": "PIX", "valor": 165}])
    _conferir_financeiro(api, venda, produtos, 10, 5)
    original = _get(api, f"/vendas/{venda['id']}/pagamentos")["pagamentos"]
    assert len(original) == 1 and original[0]["caixa_id"] == caixa["id"]
    api.expect(
        "POST",
        f"/vendas/{venda['id']}/reabrir",
        {200},
        "desconto.reabrir_paga",
        json={},
    )
    itens = {i["produto_id"]: i for i in _get(api, f"/vendas/{venda['id']}")["itens"]}
    dados["itens"] = [
        _item(
            produtos[0],
            20,
            quantidade=2,
            preco=40,
            item_id=itens[produtos[0]["id"]]["id"],
        ),
        _item(produtos[1], item_id=itens[produtos[1]["id"]]["id"]),
    ]
    editada = api.expect(
        "PUT",
        f"/vendas/{venda['id']}",
        {200},
        "desconto.alterar_quantidade_e_preco",
        json=dados,
    ).json()
    atuais = {item["produto_id"]: item for item in editada["itens"]}
    for produto in produtos:
        assert atuais[produto["id"]]["item_id_anterior"] == itens[produto["id"]]["id"]
    assert atuais[produtos[0]["id"]]["id"] != itens[produtos[0]["id"]]["id"]
    assert atuais[produtos[1]["id"]]["id"] == itens[produtos[1]["id"]]["id"]
    venda = _finalizar(api, venda["id"], [])
    assert all("item_id_anterior" not in item for item in venda["itens"])
    _conferir_venda(venda, produtos, 10, 5, 145, subtotal=160)
    _conferir_financeiro(api, venda, produtos, 10, 5)
    assert _get(api, f"/vendas/{venda['id']}/pagamentos")["pagamentos"] == original
    cupons = _get(api, "/campanhas/cupons", customer_id=cliente["id"])
    assert next(c for c in cupons if c["id"] == cupom["id"])["status"] == "used"
    print(
        f"DESCONTOS_ORIGEM venda={venda['id']} numero={venda['numero_venda']} cliente={cliente['id']} produto=20 venda=10 cupom=5 totais=165,145 recebimento_preservado=165"
    )


def test_cupom_percentual_exclui_frete_e_recalcula_ao_reabrir(api):
    _local_com_caixa_aberto(api)
    prefix = "E2E-CUPOM-PERCENTUAL-" + uuid4().hex[:8]
    cliente = _cliente(api, prefix)
    produtos = [_produto(api, prefix + suffix, preco=100) for suffix in ("-A", "-B")]
    entregador = api.expect(
        "POST",
        "/clientes/",
        {200, 201},
        "desconto.entregador_ficticio",
        json={
            "nome": prefix + "-ENTREGADOR",
            "tipo_cadastro": "fornecedor",
            "tipo_pessoa": "PF",
            "is_entregador": True,
            "entregador_ativo": True,
            "tipo_acerto_entrega": None,
        },
    ).json()
    cupom = api.expect(
        "POST",
        "/campanhas/cupons/manual",
        {200, 201},
        "desconto.cupom_percentual",
        json={
            "coupon_type": "percent",
            "discount_percent": 10,
            "channel": "pdv",
            "customer_id": cliente["id"],
            "motivo": prefix,
        },
    ).json()
    dados = _dados(cliente, produtos, prefix, global_valor=10, cupom=cupom)
    dados.update(
        tem_entrega=True,
        entregador_id=entregador["id"],
        taxa_entrega=10,
        endereco_entrega="Rua Fictícia, 123",
        cupom_discount_applied=17,
    )
    venda = api.expect(
        "POST", "/vendas", {200, 201}, "desconto.percentual_sem_frete", json=dados
    ).json()
    _conferir_venda(venda, produtos, 10, 17, 163)
    aberta = _get(api, f"/vendas/{venda['id']}")
    detalhe = next(c for c in aberta["cupons_detalhes"] if c["code"] == cupom["code"])
    assert detalhe["coupon_type"] == "percent" and detalhe["discount_percent"] == 10
    # Um cliente antigo que omite os novos campos não apaga a origem já registrada.
    itens = {i["produto_id"]: i for i in aberta["itens"]}
    dados_antigos = {
        key: value
        for key, value in dados.items()
        if key not in {"desconto_venda_valor", "cupom_code", "cupom_discount_applied"}
    }
    for item in dados_antigos["itens"]:
        item["item_id"] = itens[item["produto_id"]]["id"]
    api.expect(
        "PUT",
        f"/vendas/{venda['id']}",
        {200},
        "desconto.omissao_preserva_origem",
        json=dados_antigos,
    )
    _conferir_venda(_get(api, f"/vendas/{venda['id']}"), produtos, 10, 17, 163)
    venda = _finalizar(api, venda["id"], [{"forma_pagamento": "PIX", "valor": 163}])
    _conferir_financeiro(api, venda, produtos, 10, 17)
    api.expect(
        "POST",
        f"/vendas/{venda['id']}/reabrir",
        {200},
        "desconto.percentual_reabrir",
        json={},
    )
    aberta = _get(api, f"/vendas/{venda['id']}")
    assert (
        next(c for c in aberta["cupons_detalhes"] if c["code"] == cupom["code"])[
            "discount_percent"
        ]
        == 10
    )
    itens = {i["produto_id"]: i for i in aberta["itens"]}
    dados["itens"] = [
        _item(produtos[0], 20, quantidade=2, item_id=itens[produtos[0]["id"]]["id"]),
        _item(produtos[1], item_id=itens[produtos[1]["id"]]["id"]),
    ]
    dados["cupom_discount_applied"] = 27
    api.expect(
        "PUT",
        f"/vendas/{venda['id']}",
        {200},
        "desconto.percentual_base_maior",
        json=dados,
    )
    venda = _finalizar(api, venda["id"], [{"forma_pagamento": "PIX", "valor": 90}])
    _conferir_venda(venda, produtos, 10, 27, 253, subtotal=280)
    _conferir_financeiro(api, venda, produtos, 10, 27)
    pagamentos = _get(api, f"/vendas/{venda['id']}/pagamentos")["pagamentos"]
    assert [p["valor"] for p in pagamentos] == [163, 90]
    print(
        f"CUPOM_PERCENTUAL venda={venda['id']} numero={venda['numero_venda']} cliente={cliente['id']} frete=10 descontos_produto=20 venda=10 cupom=17,27 totais=163,253 metadados_persistidos_e_omissao_preservada"
    )


def test_precisao_monetaria_e_quantidade_iguais_na_tela_e_no_banco(api):
    _local_com_caixa_aberto(api)
    prefix = "E2E-PDV-PRECISAO-" + uuid4().hex[:8]
    cliente = _cliente(api, prefix)
    produtos = [_produto(api, prefix + suffix, preco=100) for suffix in ("-A", "-B")]
    dados = {
        "cliente_id": cliente["id"],
        "desconto_venda_valor": 0,
        "itens": [
            _item(produtos[0], quantidade=2, preco=1.005),
            _item(produtos[1], quantidade=0.33333),
        ],
        "observacoes": prefix,
        "tem_entrega": False,
    }
    venda = api.expect(
        "POST", "/vendas", {200, 201}, "desconto.precisao_criar", json=dados
    ).json()
    persistida = _get(api, f"/vendas/{venda['id']}")
    assert persistida["total"] == persistida["subtotal"] == 35.32
    itens = {i["produto_id"]: i for i in persistida["itens"]}
    assert itens[produtos[0]["id"]]["preco_unitario"] == 1.01
    assert itens[produtos[0]["id"]]["subtotal"] == 2.02
    assert itens[produtos[1]["id"]]["quantidade"] == 0.333
    assert itens[produtos[1]["id"]]["subtotal"] == 33.30
    venda = _finalizar(api, venda["id"], [{"forma_pagamento": "PIX", "valor": 35.32}])
    assert venda["total"] == 35.32
    analise = api.expect(
        "POST",
        "/formas-pagamento/analisar-venda",
        {200},
        "desconto.precisao_analise",
        json={
            "items": [
                {
                    "produto_id": produtos[0]["id"],
                    "quantidade": 0.375,
                    "preco_venda": 9.99,
                }
            ],
            "desconto_venda_valor": 0.75,
        },
    ).json()["composicao"]
    assert analise["total_produtos"] == 3.75 and analise["subtotal"] == 3
    for quantidade, preco in ((0.0004, 100), (1, 1e30)):
        dados["itens"] = [_item(produtos[0], quantidade=quantidade, preco=preco)]
        api.expect(
            "POST", "/vendas", {400, 422}, "desconto.precisao_invalida", json=dados
        )
    print(
        f"PRECISAO_PDV venda={venda['id']} preco=1.01 quantidade=0.333 total=35.32 analise_fracao=3.00 invalidos_rejeitados"
    )
