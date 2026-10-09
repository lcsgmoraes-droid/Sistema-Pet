"""Aceite HTTP de benefícios e devolução, somente na homologação fictícia local."""

import os
import time
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4

import pytest

from tests import test_plano_basico_e2e as jornada_basica

api = jornada_basica.api
e2e_config = jornada_basica.e2e_config
pytestmark = pytest.mark.e2e_long


@pytest.fixture(scope="module", autouse=True)
def somente_local_antes_da_autenticacao(e2e_config):
    assert urlparse(e2e_config.base_url).hostname in {"localhost", "127.0.0.1"}


def _get(api, path, **params):
    return api.expect("GET", path, {200}, path, params=params).json()


def _local_com_caixa_aberto(api):
    assert urlparse(api.config.base_url).hostname in {"localhost", "127.0.0.1"}
    assert _get(api, "/auth/me-multitenant")["tenant"]["name"] == (
        "CorePet Homologacao Local"
    )
    caixa = _get(api, "/caixas/aberto")
    assert caixa and caixa["status"] == "aberto", (
        "Abra o caixa de homologação antes desta jornada; ela não altera caixas."
    )
    return caixa


def _cliente(api, prefix):
    return api.expect(
        "POST",
        "/clientes/",
        {200, 201},
        "beneficios.cliente_exclusivo",
        json={
            "nome": prefix,
            "tipo_cadastro": "cliente",
            "tipo_pessoa": "PF",
            "telefone": "119" + f"{uuid4().int % 100000000:08d}",
            "observacoes": "Dados fictícios para aceite local de benefícios.",
        },
    ).json()


def _produto(api, prefix, preco=10, quantidade=20):
    produto = api.expect(
        "POST",
        "/produtos/",
        {200, 201},
        "beneficios.produto_exclusivo",
        json={
            "nome": prefix,
            "codigo": prefix,
            "unidade": "UN",
            "preco_custo": 6,
            "preco_venda": preco,
            "tipo_produto": "SIMPLES",
            "anunciar_app": False,
            "anunciar_ecommerce": False,
        },
    ).json()
    api.expect(
        "POST",
        "/estoque/entrada",
        {200, 201},
        "beneficios.estoque_sem_lote",
        json={
            "produto_id": produto["id"],
            "quantidade": quantidade,
            "custo_unitario": 6,
            "motivo": "ajuste",
            "observacao": prefix,
        },
    )
    return produto


def _item(produto_id, quantidade, preco=10, item_id=None):
    item = {
        "tipo": "produto",
        "produto_id": produto_id,
        "quantidade": quantidade,
        "preco_unitario": preco,
        "subtotal": float(Decimal(str(quantidade)) * Decimal(str(preco))),
    }
    if item_id:
        item["item_id"] = item_id
    return item


def _venda(api, cliente_id, itens, prefix):
    return api.expect(
        "POST",
        "/vendas",
        {200, 201},
        "beneficios.venda_exclusiva",
        json={
            "cliente_id": cliente_id,
            "itens": itens,
            "observacoes": prefix,
            "tem_entrega": False,
        },
    ).json()


def _finalizar(api, venda_id, pagamentos):
    api.expect(
        "POST",
        f"/vendas/{venda_id}/finalizar",
        {200},
        "beneficios.finalizar",
        json={"pagamentos": pagamentos},
    )
    venda = _get(api, f"/vendas/{venda_id}")
    assert venda["status"] == "finalizada"
    return venda


def _saldo_esperado(api, cliente_id, cashback, carimbos):
    deadline = time.monotonic() + 35
    while True:
        saldo = _get(api, f"/campanhas/clientes/{cliente_id}/saldo")
        if (
            Decimal(str(saldo["saldo_cashback"])) == Decimal(str(cashback))
            and saldo["total_carimbos"] == carimbos
        ):
            return saldo
        assert time.monotonic() < deadline, (
            f"Campanhas não atingiram cashback={cashback}, carimbos={carimbos}: {saldo}"
        )
        time.sleep(0.5)


@pytest.fixture
def regras_beneficios(api):
    _local_com_caixa_aberto(api)
    if os.getenv("E2E_ALLOW_BENEFIT_RULE_CHANGES") != "true":
        pytest.skip("Esta jornada exige janela exclusiva para ajustar regras locais.")
    campaigns = _get(api, "/campanhas")
    cashback = next(c for c in campaigns if c["campaign_type"] == "cashback")
    loyalty = next(c for c in campaigns if c["campaign_type"] == "loyalty_stamp")
    assert cashback["status"] == loyalty["status"] == "active"
    saved = [cashback, loyalty]
    quick = None
    try:
        for campaign, params in (
            (cashback, {"bronze_percent": 10}),
            (loyalty, {"min_purchase_value": 10}),
        ):
            assert set(params).issubset(campaign["params"])
            api.expect(
                "PUT",
                f"/campanhas/{campaign['id']}/parametros",
                {200},
                "beneficios.regra_temporaria",
                json={"params": params},
            )
        quick = api.expect(
            "POST",
            "/campanhas/campanhas",
            {201},
            "beneficios.recompra_exclusiva",
            json={
                "name": "E2E-RECOMPRA-" + uuid4().hex[:12],
                "campaign_type": "quick_repurchase",
                "params": {
                    "min_purchase_value": 30,
                    "coupon_type": "fixed",
                    "coupon_value": 3,
                    "coupon_valid_days": 15,
                    "cooldown_days": 0,
                    "benefit_channels": ["loja_fisica"],
                },
            },
        ).json()
        yield quick
    finally:
        errors = []
        for campaign in saved:
            try:
                api.expect(
                    "PUT",
                    f"/campanhas/{campaign['id']}/parametros",
                    {200},
                    "beneficios.restaurar_regra",
                    json={"params": campaign["params"]},
                )
            except Exception as exc:
                errors.append(f"Restaurar campanha {campaign['id']}: {exc}")
        if quick:
            try:
                api.expect(
                    "DELETE",
                    f"/campanhas/campanhas/{quick['id']}",
                    {204},
                    "beneficios.arquivar_campanha_exclusiva",
                )
            except Exception as exc:
                errors.append(f"Arquivar campanha {quick['id']}: {exc}")
        assert not errors, "Falhas na restauração local: " + "; ".join(errors)


def test_reabrir_aumentar_reduzir_remover_e_refinalizar_sem_duplicar(
    api, regras_beneficios
):
    prefix = "E2E-BENEFICIOS-" + uuid4().hex[:12]
    cliente = _cliente(api, prefix)
    primeiro = _produto(api, prefix + "-A")
    segundo = _produto(api, prefix + "-B")
    venda = _venda(
        api,
        cliente["id"],
        [_item(primeiro["id"], 3), _item(segundo["id"], 1)],
        prefix,
    )
    venda_id = venda["id"]
    _finalizar(api, venda_id, [{"forma_pagamento": "PIX", "valor": 40}])
    _saldo_esperado(api, cliente["id"], 4, 4)
    coupons = _get(
        api,
        "/campanhas/cupons",
        customer_id=cliente["id"],
        campaign_id=regras_beneficios["id"],
    )
    assert len(coupons) == 1 and coupons[0]["status"] == "active"
    original_coupon = coupons[0]
    stamp_ids = {
        stamp["id"]
        for stamp in _get(api, f"/campanhas/clientes/{cliente['id']}/carimbos")
    }

    for quantidade, cashback, carimbos, pagamento, cupom_ativo in (
        (5, 6, 6, 20, True),
        (1, 2, 2, 0, False),
        (0, 1, 1, 0, False),
        (0, 1, 1, 0, False),
    ):
        api.expect(
            "POST", f"/vendas/{venda_id}/reabrir", {200}, "beneficios.reabrir", json={}
        )
        _saldo_esperado(api, cliente["id"], 0, 0)
        atual = _get(api, f"/vendas/{venda_id}")
        ids = {item["produto_id"]: item["id"] for item in atual["itens"]}
        itens = [_item(segundo["id"], 1, item_id=ids[segundo["id"]])]
        if quantidade:
            itens.insert(
                0, _item(primeiro["id"], quantidade, item_id=ids[primeiro["id"]])
            )
        api.expect(
            "PUT",
            f"/vendas/{venda_id}",
            {200},
            "beneficios.editar_quantidade",
            json={"cliente_id": cliente["id"], "itens": itens, "observacoes": prefix},
        )
        pagamentos = (
            [{"forma_pagamento": "PIX", "valor": pagamento}] if pagamento else []
        )
        finalizada = _finalizar(api, venda_id, pagamentos)
        assert finalizada["total"] == (quantidade + 1) * 10
        _saldo_esperado(api, cliente["id"], cashback, carimbos)
        assert _get(api, f"/produtos/{primeiro['id']}")["estoque_atual"] == (
            20 - quantidade
        )
        assert _get(api, f"/produtos/{segundo['id']}")["estoque_atual"] == 19
        coupons = _get(
            api,
            "/campanhas/cupons",
            customer_id=cliente["id"],
            campaign_id=regras_beneficios["id"],
        )
        assert len(coupons) == 1
        assert coupons[0]["id"] == original_coupon["id"]
        assert coupons[0]["code"] == original_coupon["code"]
        assert coupons[0]["valid_until"] == original_coupon["valid_until"]
        assert coupons[0]["discount_value"] == original_coupon["discount_value"]
        assert coupons[0]["status"] == ("active" if cupom_ativo else "voided")
        stamps = _get(
            api,
            f"/campanhas/clientes/{cliente['id']}/carimbos",
            incluir_estornados="true",
        )
        assert len(stamps) == 6
        assert stamp_ids.issubset({stamp["id"] for stamp in stamps})
        assert sum(stamp["voided_at"] is None for stamp in stamps) == carimbos

    extrato = _get(api, f"/campanhas/clientes/{cliente['id']}/cashback/extrato")
    assert sum(Decimal(str(t["amount"])) for t in extrato["transacoes"]) == 1
    assert len(extrato["transacoes"]) == 9
    print(
        f"BENEFICIOS venda={venda_id} numero={finalizada['numero_venda']} "
        f"cliente={cliente['id']} totais=40,60,20,10,10 cashback=4,6,2,1,1 "
        f"carimbos=4,6,2,1,1 cupom={original_coupon['code']} sem_duplicacao"
    )


def test_reabrir_alterar_preco_e_desconto_ajusta_beneficios_sem_novo_recebimento(
    api, regras_beneficios
):
    caixa = _local_com_caixa_aberto(api)
    prefix = "E2E-PRECO-BENEFICIOS-" + uuid4().hex[:12]
    cliente = _cliente(api, prefix)
    produto = _produto(api, prefix, preco=20)
    venda = _venda(api, cliente["id"], [_item(produto["id"], 2, 20)], prefix)
    venda_id = venda["id"]
    _finalizar(api, venda_id, [{"forma_pagamento": "PIX", "valor": 40}])
    _saldo_esperado(api, cliente["id"], 4, 4)
    coupons = _get(
        api,
        "/campanhas/cupons",
        customer_id=cliente["id"],
        campaign_id=regras_beneficios["id"],
    )
    assert len(coupons) == 1 and coupons[0]["status"] == "active"
    original_coupon = coupons[0]
    original_payments = _get(api, f"/vendas/{venda_id}/pagamentos")["pagamentos"]
    expected_payments = original_payments
    assert len(original_payments) == 1 and original_payments[0]["valor"] == 40

    # Duas unidades em todas as etapas: primeiro varia o preço, depois o desconto.
    for preco, desconto, total, cashback, carimbos, pagamento in (
        (30, 0, 60, 6, 6, 20),
        (10, 0, 20, 2, 2, 0),
        (5, 0, 10, 1, 1, 0),
        (5, 0, 10, 1, 1, 0),
        (20, 25, 15, "1.50", 1, 0),
        (20, 20, 20, 2, 2, 0),
        (20, 0, 40, 4, 4, 0),
    ):
        api.expect(
            "POST", f"/vendas/{venda_id}/reabrir", {200}, "preco.reabrir", json={}
        )
        _saldo_esperado(api, cliente["id"], 0, 0)
        reopened_coupons = _get(
            api,
            "/campanhas/cupons",
            customer_id=cliente["id"],
            campaign_id=regras_beneficios["id"],
        )
        assert len(reopened_coupons) == 1
        assert reopened_coupons[0]["id"] == original_coupon["id"]
        assert reopened_coupons[0]["status"] == "voided"
        atual = _get(api, f"/vendas/{venda_id}")
        assert len(atual["itens"]) == 1
        item = atual["itens"][0]
        assert item["produto_id"] == produto["id"] and item["quantidade"] == 2
        api.expect(
            "PUT",
            f"/vendas/{venda_id}",
            {200},
            "preco.editar_preco_ou_desconto",
            json={
                "cliente_id": cliente["id"],
                "itens": [_item(produto["id"], 2, preco, item_id=item["id"])],
                "desconto_valor": desconto,
                "observacoes": prefix,
            },
        )
        pagamentos = (
            [{"forma_pagamento": "PIX", "valor": pagamento}] if pagamento else []
        )
        finalizada = _finalizar(api, venda_id, pagamentos)
        assert finalizada["total"] == total
        assert len(finalizada["itens"]) == 1
        assert finalizada["itens"][0]["quantidade"] == 2
        assert finalizada["itens"][0]["preco_unitario"] == preco
        assert _get(api, f"/produtos/{produto['id']}")["estoque_atual"] == 18
        _saldo_esperado(api, cliente["id"], cashback, carimbos)
        receipts = _get(api, f"/vendas/{venda_id}/pagamentos")
        if pagamento:
            assert len(receipts["pagamentos"]) == 2
            assert receipts["pagamentos"][0] == original_payments[0]
            assert receipts["pagamentos"][1]["valor"] == 20
            expected_payments = receipts["pagamentos"]
        else:
            assert receipts["pagamentos"] == expected_payments
        assert sum(p["valor"] for p in receipts["pagamentos"]) == 60
        assert all(p["caixa_id"] == caixa["id"] for p in receipts["pagamentos"])
        assert receipts["valor_restante"] == 0
        coupons = _get(
            api,
            "/campanhas/cupons",
            customer_id=cliente["id"],
            campaign_id=regras_beneficios["id"],
        )
        assert len(coupons) == 1
        for key in ("id", "code", "valid_until", "discount_value"):
            assert coupons[0][key] == original_coupon[key]
        assert coupons[0]["status"] == ("active" if total >= 30 else "voided")

    auditoria = _get(api, f"/caixas/{caixa['id']}/auditoria")
    received = [p for p in auditoria["pagamentos"] if p["venda_id"] == venda_id]
    assert len(received) == 2 and sum(p["valor"] for p in received) == 60
    assert not [m for m in auditoria["movimentacoes"] if m["venda_id"] == venda_id]
    stamps = _get(
        api,
        f"/campanhas/clientes/{cliente['id']}/carimbos",
        incluir_estornados="true",
    )
    assert len(stamps) == 6
    assert sum(stamp["voided_at"] is None for stamp in stamps) == 4
    extrato = _get(api, f"/campanhas/clientes/{cliente['id']}/cashback/extrato")
    assert sum(Decimal(str(t["amount"])) for t in extrato["transacoes"]) == 4
    print(
        f"PRECO_BENEFICIOS venda={venda_id} numero={finalizada['numero_venda']} "
        f"cliente={cliente['id']} quantidade=2 estoque=18 "
        "totais=40,60,20,10,10,15,20,40 cashback=4,6,2,1,1,1.5,2,4 "
        "carimbos=4,6,2,1,1,1,2,4 recebimentos=40+20 sem_duplicacao"
    )


def preparar_venda_cartao_pendente(api, prefix=None):
    """Cria venda separada para a UI ou para a jornada HTTP de devolução."""
    caixa = _local_com_caixa_aberto(api)
    prefix = prefix or "E2E-CARTAO-" + uuid4().hex[:12]
    cliente = _cliente(api, prefix)
    produto = _produto(api, prefix, preco=56.90, quantidade=3)
    forma = next(
        f
        for f in _get(api, "/financeiro/formas-pagamento")
        if f["tipo"] == "cartao_credito" and f["ativo"]
    )
    operadora = api.expect(
        "POST",
        "/operadoras-cartao",
        {201},
        "devolucao.operadora_ficticia",
        json={
            "nome": prefix,
            "codigo": prefix,
            "padrao": False,
            "bandeira_padrao": "visa",
        },
    ).json()
    api.expect(
        "PUT",
        f"/operadoras-cartao/{operadora['id']}/taxas",
        {200},
        "devolucao.repasse_futuro",
        json={
            "taxas": [
                {
                    "bandeira": "visa",
                    "modalidade": "credito",
                    "parcelas": 1,
                    "taxa_percentual": 3,
                    "prazo_recebimento_dias": 30,
                }
            ]
        },
    )
    venda = _venda(api, cliente["id"], [_item(produto["id"], 1, 56.90)], prefix)
    venda = _finalizar(
        api,
        venda["id"],
        [
            {
                "forma_pagamento": forma["nome"],
                "forma_pagamento_id": forma["id"],
                "valor": 56.90,
                "numero_parcelas": 1,
                "operadora_id": operadora["id"],
                "bandeira": "visa",
                "modalidade_cartao": "credito",
                "nsu_cartao": uuid4().hex[:12],
            }
        ],
    )
    contas = _get(api, "/contas-receber/", cliente_id=cliente["id"])
    assert len(contas) == 1
    assert contas[0]["status"] == "pendente" and contas[0]["valor_recebido"] == 0
    assert _get(api, f"/produtos/{produto['id']}")["estoque_atual"] == 2
    return {
        "venda": venda,
        "cliente": cliente,
        "produto": produto,
        "conta": contas[0],
        "caixa": caixa,
    }


def test_cartao_com_repasse_pendente_devolve_credito_uma_vez(api):
    cenario = preparar_venda_cartao_pendente(api)
    venda, cliente, produto = (cenario[key] for key in ("venda", "cliente", "produto"))
    item = venda["itens"][0]
    saldo_antes = _get(api, f"/clientes/{cliente['id']}")["credito"]
    caixa_id = cenario["caixa"]["id"]
    movimentos_antes = [
        movimento
        for movimento in _get(api, f"/caixas/{caixa_id}/auditoria")["movimentacoes"]
        if movimento.get("venda_id") == venda["id"]
    ]
    assert movimentos_antes == []
    dados = {
        "itens": [
            {"item_id": item["id"], "produto_id": produto["id"], "quantidade": 1}
        ],
        "motivo": "Aceite local: cartão pago, repasse bancário futuro.",
        "gerar_credito": True,
        "chave_operacao": str(uuid4()),
    }
    previa = api.expect(
        "POST",
        f"/vendas/{venda['id']}/devolucao/previa",
        {200},
        "devolucao.cartao_previa",
        json=dados,
    ).json()
    assert previa["valor_total_devolucao"] == 56.90
    dados["valor_total_previsto"] = previa["valor_total_devolucao"]
    primeira = api.expect(
        "POST",
        f"/vendas/{venda['id']}/devolucao",
        {200},
        "devolucao.cartao_credito",
        json=dados,
    ).json()
    repetida = api.expect(
        "POST",
        f"/vendas/{venda['id']}/devolucao",
        {200},
        "devolucao.repeticao_segura",
        json=dados,
    ).json()
    assert primeira == repetida
    assert primeira["status_venda"] == "devolvida_total"
    assert primeira["valor_total_devolucao"] == 56.90
    assert "movimentacao_caixa_id" not in primeira
    assert [
        movimento
        for movimento in _get(api, f"/caixas/{caixa_id}/auditoria")["movimentacoes"]
        if movimento.get("venda_id") == venda["id"]
    ] == movimentos_antes
    assert Decimal(str(_get(api, f"/clientes/{cliente['id']}")["credito"])) == (
        Decimal(str(saldo_antes or 0)) + Decimal("56.90")
    )
    assert _get(api, f"/produtos/{produto['id']}")["estoque_atual"] == 3
    contas = _get(api, "/contas-receber/", cliente_id=cliente["id"])
    assert [(c["id"], c["status"], c["valor_recebido"]) for c in contas] == (
        [(cenario["conta"]["id"], "pendente", 0)]
    )
    print(
        f"DEVOLUCAO venda={venda['id']} numero={venda['numero_venda']} "
        f"cliente={cliente['id']} credito=56.90 devolucao={primeira['devolucao_id']} "
        f"repasse_pendente conta={cenario['conta']['id']} repeticao_sem_duplicacao"
    )
