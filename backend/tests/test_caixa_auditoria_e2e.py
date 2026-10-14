"""Jornada HTTP do caixa, restrita à empresa fictícia da homologação local."""

from urllib.parse import urlparse
from uuid import uuid4
from dataclasses import replace

import pytest

from tests.test_plano_basico_e2e import (
    E2EApi,
    _create_cliente,
    _create_produto,
    _ensure_caixa_aberto,
)

from tests import test_plano_basico_e2e as jornada_basica

pytestmark = pytest.mark.e2e_long
api = jornada_basica.api
e2e_config = jornada_basica.e2e_config


def _get(api: E2EApi, path):
    return api.expect("GET", path, {200}, path).json()


def _fechar(api: E2EApi, caixa_id):
    resumo = _get(api, f"/caixas/{caixa_id}/resumo")
    api.expect(
        "POST",
        f"/caixas/{caixa_id}/fechar",
        {200},
        "caixa.fechar",
        json={
            "valor_informado": resumo["totais"]["saldo_atual"],
            "observacoes_fechamento": f"{api.config.prefix} auditoria",
        },
    )


def test_recebimento_em_outro_caixa_e_historico_auditavel(api: E2EApi):
    if urlparse(api.config.base_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.skip("Esta jornada cria dados somente na homologação local.")
    me = _get(api, "/auth/me-multitenant")
    if me["tenant"]["name"] != "CorePet Homologacao Local":
        pytest.skip("Esta jornada exige a empresa fictícia CorePet Homologacao Local.")
    api.config = replace(
        api.config, prefix=f"{api.config.prefix}-CAIXA-{uuid4().int % 10000000000:010d}"
    )
    _ensure_caixa_aberto(api)
    original = _get(api, "/caixas/aberto")
    cliente_id = _create_cliente(api)
    produto_id, estoque_inicial = _create_produto(api)
    venda = api.expect(
        "POST",
        "/vendas",
        {200, 201},
        "caixa.venda_anterior",
        json={
            "cliente_id": cliente_id,
            "itens": [
                {
                    "tipo": "produto",
                    "produto_id": produto_id,
                    "quantidade": 3,
                    "preco_unitario": 10,
                    "subtotal": 30,
                }
            ],
            "observacoes": f"{api.config.prefix} recebimento em outro caixa",
            "tem_entrega": False,
        },
    ).json()
    venda_id = venda["id"]
    estoque_apos_criacao = float(_get(api, f"/produtos/{produto_id}")["estoque_atual"])
    assert estoque_apos_criacao == estoque_inicial - 3
    api.expect(
        "POST",
        f"/vendas/{venda_id}/finalizar",
        {200},
        "caixa.baixa_parcial",
        json={
            "pagamentos": [{"forma_pagamento": "PIX", "valor": 5, "numero_parcelas": 1}]
        },
    )
    assert (
        float(_get(api, f"/produtos/{produto_id}")["estoque_atual"])
        == estoque_apos_criacao
    )
    _fechar(api, original["id"])
    resumo_original = _get(api, f"/caixas/{original['id']}/resumo")
    atual = api.expect(
        "POST",
        "/caixas/abrir",
        {200, 201},
        "caixa.abrir_recebedor",
        json={
            "valor_abertura": 100,
            "observacoes_abertura": f"{api.config.prefix} auditoria",
        },
    ).json()
    try:
        api.expect(
            "POST",
            f"/vendas/{venda_id}/finalizar",
            {200},
            "caixa.receber_venda_anterior",
            json={
                "pagamentos": [
                    {"forma_pagamento": "PIX", "valor": 10, "numero_parcelas": 1},
                    {"forma_pagamento": "Dinheiro", "valor": 15, "numero_parcelas": 1},
                ]
            },
        )
        assert (
            float(_get(api, f"/produtos/{produto_id}")["estoque_atual"])
            == estoque_apos_criacao
        )
        resumo = _get(api, f"/caixas/{atual['id']}/resumo")
        assert resumo["total_recebido"] == 25
        assert resumo["total_vendido"] == 0
        assert resumo["totais"]["saldo_atual"] == 115
        assert resumo["recebimentos_por_forma_pagamento"]["PIX"]["total"] == 10
        assert resumo["pagamentos_vendas_por_forma_pagamento"] == {}
        assert resumo["pagamentos_vendas_sem_caixa"]["quantidade"] == 0
        assert any(
            item["venda_id"] == venda_id
            for item in _get(api, f"/caixas/{original['id']}/vendas")
        )
        original_depois = _get(api, f"/caixas/{original['id']}/resumo")
        assert original_depois["total_recebido"] == resumo_original["total_recebido"]
        assert original_depois["total_vendido"] == resumo_original["total_vendido"]
        assert original_depois["pagamentos_vendas_por_forma_pagamento"]["PIX"][
            "total"
        ] == pytest.approx(
            resumo_original["pagamentos_vendas_por_forma_pagamento"]["PIX"]["total"]
            + 10
        )
        assert original_depois["pagamentos_vendas_por_forma_pagamento"]["Dinheiro"][
            "total"
        ] == pytest.approx(
            resumo_original["pagamentos_vendas_por_forma_pagamento"]
            .get("Dinheiro", {})
            .get("total", 0)
            + 15
        )
        detalhe = _get(api, f"/caixas/{atual['id']}/vendas?forma_pagamento=PIX")
        assert len(detalhe) == 1 and detalhe[0]["venda_id"] == venda_id
        assert detalhe[0]["valor_nesta_forma"] == 10

        _fechar(api, atual["id"])
        auditoria = _get(api, f"/caixas/{atual['id']}/auditoria")
        assert len(auditoria["vendas"]) == 1
        assert len(auditoria["movimentacoes"]) == 1
        assert len(auditoria["pagamentos"]) == 1
        item = auditoria["vendas"][0]
        assert [pagamento["valor"] for pagamento in item["pagamentos"]] == [5, 10, 15]
        assert [pagamento["caixa_id"] for pagamento in item["pagamentos"]] == [
            original["id"],
            atual["id"],
            atual["id"],
        ]
        assert sum(recebimento["valor"] for recebimento in item["recebimentos"]) == 25
        conferencia = {
            "tipo_item": "venda",
            "item_id": item["id"],
            "conferido": True,
            "assinatura": item["assinatura"],
        }
        api.expect(
            "POST",
            f"/caixas/{atual['id']}/auditoria/conferencia",
            {200},
            "caixa.conferir_venda",
            json=conferencia,
        )
        assert _get(api, f"/caixas/{atual['id']}/auditoria")["vendas"][0]["conferido"]
        api.expect(
            "POST",
            f"/caixas/{atual['id']}/reabrir",
            {200},
            "caixa.reabrir",
            json={"motivo": "Teste local de reabertura e preservação do fechamento"},
        )
        historico = _get(api, f"/caixas/{atual['id']}/auditoria")["historico"]
        reabertura = next(
            evento for evento in historico if evento["acao"] == "caixa_reaberto"
        )
        assert reabertura["anterior"]["resumo"]["caixa"]["valor_informado"] == 115
        assert reabertura["anterior"]["resumo"]["total_recebido"] == 25
        api.expect(
            "POST",
            f"/vendas/{venda_id}/reabrir",
            {200},
            "caixa.venda_muda",
            json={},
        )
        revisada = _get(api, f"/caixas/{atual['id']}/auditoria")
        assert not revisada["vendas"][0]["conferido"]
        assert revisada["resumo"]["total_recebido"] == 25
        api.expect(
            "POST",
            f"/caixas/{atual['id']}/auditoria/conferencia",
            {409},
            "caixa.conferencia_desatualizada",
            json=conferencia,
        )
        api.expect(
            "POST",
            f"/vendas/{venda_id}/finalizar",
            {200},
            "caixa.refinalizar",
            json={"pagamentos": []},
        )
        assert _get(api, f"/caixas/{atual['id']}/resumo")["total_recebido"] == 25
        assert (
            float(_get(api, f"/produtos/{produto_id}")["estoque_atual"])
            == estoque_apos_criacao
        )
    finally:
        aberto = _get(api, "/caixas/aberto")
        if aberto and aberto["id"] == atual["id"]:
            _fechar(api, atual["id"])


def test_auditoria_venda_mista_quatro_formas_mantem_caixa_aberto(api: E2EApi):
    if urlparse(api.config.base_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.skip("Esta jornada cria dados somente na homologação local.")
    me = _get(api, "/auth/me-multitenant")
    if me["tenant"]["name"] != "CorePet Homologacao Local":
        pytest.skip("Esta jornada exige a empresa fictícia CorePet Homologacao Local.")
    api.config = replace(
        api.config, prefix=f"E2E-PB-AUD4-{uuid4().int % 10000000000:010d}"
    )
    _ensure_caixa_aberto(api)
    caixa = _get(api, "/caixas/aberto")
    anterior = _get(api, f"/caixas/{caixa['id']}/resumo")
    cliente_id = _create_cliente(api)
    produto_id, estoque_inicial = _create_produto(api)
    formas = _get(api, "/financeiro/formas-pagamento")
    credito = next(f for f in formas if f["ativo"] and f["tipo"] == "cartao_credito")
    debito = next(f for f in formas if f["ativo"] and f["tipo"] == "cartao_debito")
    operadora = api.expect(
        "POST",
        "/operadoras-cartao",
        {201},
        "auditoria.operadora_ficticia",
        json={
            "nome": api.config.prefix,
            "codigo": api.config.prefix,
            "padrao": False,
            "bandeira_padrao": "visa",
        },
    ).json()
    api.expect(
        "PUT",
        f"/operadoras-cartao/{operadora['id']}/taxas",
        {200},
        "auditoria.taxas_ficticias",
        json={
            "taxas": [
                {
                    "bandeira": "visa",
                    "modalidade": modalidade,
                    "parcelas": 1,
                    "taxa_percentual": 0,
                    "prazo_recebimento_dias": 1,
                }
                for modalidade in ["credito", "debito"]
            ]
        },
    )
    venda = api.expect(
        "POST",
        "/vendas",
        {200, 201},
        "auditoria.venda_mista",
        json={
            "cliente_id": cliente_id,
            "itens": [
                {
                    "tipo": "produto",
                    "produto_id": produto_id,
                    "quantidade": 1,
                    "preco_unitario": 100,
                    "desconto_item": 0,
                    "subtotal": 100,
                }
            ],
            "desconto_venda_valor": 0,
            "observacoes": api.config.prefix,
            "tem_entrega": False,
        },
    ).json()
    pagamentos = [
        {"forma_pagamento": "Dinheiro", "valor": 10, "numero_parcelas": 1},
        {"forma_pagamento": "PIX", "valor": 20, "numero_parcelas": 1},
    ]
    for forma, valor, modalidade in [(credito, 30, "credito"), (debito, 40, "debito")]:
        pagamentos.append(
            {
                "forma_pagamento": forma["nome"],
                "forma_pagamento_id": forma["id"],
                "valor": valor,
                "numero_parcelas": 1,
                "operadora_id": operadora["id"],
                "bandeira": "visa",
                "modalidade_cartao": modalidade,
                "nsu_cartao": uuid4().hex[:12],
            }
        )
    api.expect(
        "POST",
        f"/vendas/{venda['id']}/finalizar",
        {200},
        "auditoria.quatro_formas",
        json={
            "pagamentos": pagamentos,
            "nao_gerar_beneficios": True,
            "justificativa_sem_beneficios": "Teste local exclusivo de auditoria de caixa",
        },
    )
    auditoria = _get(api, f"/caixas/{caixa['id']}/auditoria")
    item = next(item for item in auditoria["vendas"] if item["id"] == venda["id"])
    assert item["total"] == item["valor_nesta_forma"] == 100
    assert len(item["pagamentos"]) == len(item["recebimentos"]) == 4
    assert all(pagamento["caixa_id"] == caixa["id"] for pagamento in item["pagamentos"])
    esperado = {
        pagamento["forma_pagamento"]: pagamento["valor"] for pagamento in pagamentos
    }
    assert {
        pagamento["forma_pagamento"]: pagamento["valor"]
        for pagamento in item["pagamentos"]
    } == esperado
    resumo = auditoria["resumo"]
    assert resumo["total_vendido"] == pytest.approx(anterior["total_vendido"] + 100)
    assert resumo["total_recebido"] == pytest.approx(anterior["total_recebido"] + 100)
    assert resumo["totais"]["saldo_atual"] == pytest.approx(
        anterior["totais"]["saldo_atual"] + 10
    )
    for forma, valor in esperado.items():
        for campo in [
            "pagamentos_vendas_por_forma_pagamento",
            "recebimentos_por_forma_pagamento",
        ]:
            total_anterior = anterior[campo].get(forma, {}).get("total", 0)
            assert resumo[campo][forma]["total"] == pytest.approx(
                total_anterior + valor
            )
    assert (
        resumo["pagamentos_vendas_sem_caixa"] == anterior["pagamentos_vendas_sem_caixa"]
    )
    assert (
        float(_get(api, f"/produtos/{produto_id}")["estoque_atual"])
        == estoque_inicial - 1
    )
    assert _get(api, "/caixas/aberto")["id"] == caixa["id"]
    print(
        f"AUDITORIA_QUATRO_FORMAS caixa={caixa['id']} numero={caixa['numero_caixa']} "
        f"venda={venda['id']} numero_venda={venda['numero_venda']} "
        f"cliente={cliente_id} produto={produto_id} nome={api.config.prefix} "
        "total=100 dinheiro=10 pix=20 credito=30 debito=40 caixa_aberto=true"
    )
