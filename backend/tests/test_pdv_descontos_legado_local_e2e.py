"""Preservação dos valores de vendas legadas, somente na homologação local."""

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


def _conferir_valores_legados(venda, produtos, cupom):
    assert venda["desconto_venda_valor"] is None
    assert venda["desconto_origem_legado"] is True
    assert venda["subtotal"] == venda["total"] == 180
    assert venda["desconto_valor"] == venda["desconto_itens_valor"] == 20
    assert venda["cupom_code"] == cupom["code"]
    assert venda["cupom_discount_applied"] == 10
    itens = {item["produto_id"]: item for item in venda["itens"]}
    assert len(itens) == 2
    for produto, desconto, subtotal in zip(produtos, (15, 5), (85, 95)):
        item = itens[produto["id"]]
        assert item["quantidade"] == 1
        assert item["preco_unitario"] == 100
        # Preservar o campo histórico não prova a origem manual de cada parcela.
        assert item["desconto_item"] == desconto
        assert item["subtotal"] == subtotal
    return itens


def _conferir_devolucoes_e_relatorio(api, venda, produtos, itens):
    for produto, valor in zip(produtos, (85, 95)):
        previa = api.expect(
            "POST",
            f"/vendas/{venda['id']}/devolucao/previa",
            {200},
            "legado.previa_liquida_preservada",
            json={
                "itens": [
                    {
                        "item_id": itens[produto["id"]]["id"],
                        "produto_id": produto["id"],
                        "quantidade": 1,
                    }
                ],
                "motivo": "Aceite fictício da preservação de valores legados.",
                "gerar_credito": True,
                "chave_operacao": str(uuid4()),
            },
        ).json()
        assert previa["valor_total_devolucao"] == valor

    dia = venda["data_venda"][:10]
    relatorio = _get(api, "/relatorios/vendas/relatorio", data_inicio=dia, data_fim=dia)
    registro = next(v for v in relatorio["lista_vendas"] if v["id"] == venda["id"])
    assert registro["desconto_venda_valor"] is None
    assert registro["desconto_origem_legado"] is True
    linhas = {item["produto_id"]: item for item in registro["itens"]}
    for produto, valor in zip(produtos, (85, 95)):
        linha = linhas[produto["id"]]
        # O relatório pode reclassificar cupom e desconto sem mudar o líquido.
        bruto = Decimal(str(linha["venda_bruta"]))
        manual = Decimal(str(linha["desconto"]))
        cupom = Decimal(str(linha["cupom_desconto"]))
        assert bruto - manual - cupom == valor
    assert sum(Decimal(str(i["desconto"])) for i in linhas.values()) == 10
    assert sum(Decimal(str(i["cupom_desconto"])) for i in linhas.values()) == 10


def test_reabrir_sem_editar_preserva_descontos_legados_recebimentos_e_devolucao(api):
    caixa = _local_com_caixa_aberto(api)
    assert api.config.tenant_id == "fcbaa106-3b50-4b75-876a-614d157aa670"
    prefix = "E2E-DESCONTOS-LEGADO-" + uuid4().hex[:8]
    cliente = _cliente(api, prefix)
    produtos = [_produto(api, prefix + suffix, preco=100) for suffix in ("-A", "-B")]
    cupom = api.expect(
        "POST",
        "/campanhas/cupons/manual",
        {200, 201},
        "legado.cupom_exclusivo",
        json={
            "coupon_type": "fixed",
            "discount_value": 10,
            "channel": "pdv",
            "customer_id": cliente["id"],
            "motivo": prefix,
        },
    ).json()
    dados = {
        "cliente_id": cliente["id"],
        "itens": [
            {
                "tipo": "produto",
                "produto_id": produto["id"],
                "quantidade": 1,
                "preco_unitario": 100,
                "desconto_item": desconto,
                "subtotal": subtotal,
            }
            for produto, desconto, subtotal in zip(produtos, (15, 5), (85, 95))
        ],
        # Omitir G mantém o contrato antigo; o cupom já compõe o agregado.
        "desconto_valor": 20,
        "cupom_code": cupom["code"],
        "cupom_discount_applied": 10,
        "tem_entrega": False,
        "observacoes": prefix,
    }
    venda = api.expect(
        "POST", "/vendas", {200, 201}, "legado.criar_sem_nova_origem", json=dados
    ).json()
    _conferir_valores_legados(venda, produtos, cupom)
    venda = _finalizar(api, venda["id"], [{"forma_pagamento": "PIX", "valor": 180}])
    itens = _conferir_valores_legados(venda, produtos, cupom)
    _conferir_devolucoes_e_relatorio(api, venda, produtos, itens)
    original = _get(api, f"/vendas/{venda['id']}/pagamentos")["pagamentos"]
    assert len(original) == 1
    assert original[0]["valor"] == 180
    assert original[0]["caixa_id"] == caixa["id"]
    assert original[0]["forma_pagamento"] == "PIX"
    for produto in produtos:
        assert _get(api, f"/produtos/{produto['id']}")["estoque_atual"] == 19

    api.expect(
        "POST",
        f"/vendas/{venda['id']}/reabrir",
        {200},
        "legado.reabrir_paga",
        json={},
    )
    aberta = _get(api, f"/vendas/{venda['id']}")
    assert {i["produto_id"]: i["id"] for i in aberta["itens"]} == {
        produto_id: item["id"] for produto_id, item in itens.items()
    }
    dados["desconto_venda_valor"] = None
    for item in dados["itens"]:
        item["item_id"] = itens[item["produto_id"]]["id"]
    api.expect(
        "PUT",
        f"/vendas/{venda['id']}",
        {200},
        "legado.salvar_mesmos_valores_com_origem_nula",
        json=dados,
    )
    _conferir_valores_legados(_get(api, f"/vendas/{venda['id']}"), produtos, cupom)
    venda = _finalizar(api, venda["id"], [])
    itens = _conferir_valores_legados(venda, produtos, cupom)
    _conferir_devolucoes_e_relatorio(api, venda, produtos, itens)
    pagamentos = _get(api, f"/vendas/{venda['id']}/pagamentos")
    assert pagamentos["pagamentos"] == original
    assert pagamentos["valor_restante"] == 0
    auditoria = _get(api, f"/caixas/{caixa['id']}/auditoria")
    recebimentos = [p for p in auditoria["pagamentos"] if p["venda_id"] == venda["id"]]
    assert len(recebimentos) == 1 and recebimentos[0]["valor"] == 180
    assert not [m for m in auditoria["movimentacoes"] if m["venda_id"] == venda["id"]]
    for produto in produtos:
        assert _get(api, f"/produtos/{produto['id']}")["estoque_atual"] == 19
    print(
        f"DESCONTOS_LEGADO venda={venda['id']} numero={venda['numero_venda']} "
        f"cliente={cliente['id']} produtos={[p['id'] for p in produtos]} "
        "G=None agregado=20 cupom=10 total=180 recebimento_unico=180 devolucoes=85,95"
    )
