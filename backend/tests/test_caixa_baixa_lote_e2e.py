"""Baixa em lote local que reutiliza um caixa explicitamente indicado pelo operador."""

import json
import os
import subprocess
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

import pytest

from tests import test_plano_basico_e2e as jornada_basica
from tests.test_plano_basico_e2e import E2EApi, _create_cliente, _create_produto

pytestmark = pytest.mark.e2e_long
api = jornada_basica.api
e2e_config = jornada_basica.e2e_config


def _get(api: E2EApi, path):
    return api.expect("GET", path, {200}, path).json()


def _pagamentos(api, venda_id):
    return _get(api, f"/vendas/{venda_id}/pagamentos")


def _verificar_estoque(api, produto_id, esperado):
    assert float(_get(api, f"/produtos/{produto_id}")["estoque_atual"]) == esperado


def _datar_vendas_ficticias(
    container, *, tenant_id, vendas, datas, caixa_id, observacoes, marker
):
    """Prepara somente os registros fictícios criados nesta execução, sem alterar permissões."""
    script = """
import json, os, sys
from uuid import UUID
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

dados = json.load(sys.stdin)
assert os.environ.get('ENVIRONMENT') == 'staging', 'Seeding exige staging local'
url = make_url(os.environ['DATABASE_URL'])
assert url.get_backend_name() == 'postgresql' and url.database == 'corepet_homolog'
assert dados['tenant_id'] == 'fcbaa106-3b50-4b75-876a-614d157aa670'
assert len(dados['vendas']) == 2 and len(set(dados['vendas'])) == 2
assert str(UUID(dados['marker'])).replace('-', '') == dados['marker']
assert dados['observacoes'].startswith('E2E-PB-') and '-LOTE-' in dados['observacoes']
assert dados['marker'] in dados['observacoes']
with create_engine(url).begin() as db:
    assert db.scalar(text('SELECT current_database()')) == 'corepet_homolog'
    assert db.scalar(text('SELECT name FROM tenants WHERE id::text = :tenant'),
                     {'tenant': dados['tenant_id']}) == 'CorePet Homologacao Local'
    assert db.scalar(text('SELECT status FROM caixas WHERE id = :id AND tenant_id::text = :tenant'),
                     {'id': dados['caixa_id'], 'tenant': dados['tenant_id']}) == 'fechado'
    for venda_id, data in zip(dados['vendas'], dados['datas']):
        atualizada = db.execute(text('''
            UPDATE vendas SET data_venda = CAST(:data AS timestamp), caixa_id = :caixa_id
            WHERE id = :venda_id AND tenant_id::text = :tenant AND observacoes = :observacoes
              AND status = 'aberta'
              AND NOT EXISTS (SELECT 1 FROM venda_pagamentos WHERE venda_id = :venda_id)
        '''), {'data': data, 'caixa_id': dados['caixa_id'], 'venda_id': venda_id,
                'tenant': dados['tenant_id'], 'observacoes': dados['observacoes']})
        assert atualizada.rowcount == 1, 'Registro não pertence a esta jornada ou já foi recebido'
print('Duas vendas fictícias datadas no banco local.')
"""
    resultado = subprocess.run(
        ["docker", "exec", "-i", container, "python", "-c", script],
        input=json.dumps(
            {
                "tenant_id": tenant_id,
                "vendas": vendas,
                "datas": [data.isoformat() for data in datas],
                "caixa_id": caixa_id,
                "observacoes": observacoes,
                "marker": marker,
            }
        ),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr[-2000:]


def test_baixa_lote_vendas_antigas_no_caixa_atual_sem_duplicar(api: E2EApi):
    if urlparse(api.config.base_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.skip("Esta jornada cria dados somente na homologação local.")
    if (
        _get(api, "/auth/me-multitenant")["tenant"]["name"]
        != "CorePet Homologacao Local"
    ):
        pytest.skip("Esta jornada exige a empresa fictícia CorePet Homologacao Local.")
    caixa_indicado = os.getenv("E2E_REUSE_CAIXA_ID")
    if not caixa_indicado:
        pytest.skip("Informe E2E_REUSE_CAIXA_ID para receber no caixa já aberto.")
    container = os.getenv("E2E_LOCAL_SEED_CONTAINER")
    if container != "corepet-homolog-backend-1":
        pytest.skip(
            "Informe o container local explícito para preparar vendas fictícias anteriores."
        )
    atual = _get(api, "/caixas/aberto")
    assert atual and str(atual["id"]) == caixa_indicado
    assert atual["status"] == "aberto"
    caixa_id = atual["id"]

    hoje = datetime.now(timezone(timedelta(hours=-3))).replace(tzinfo=None)
    datas = [
        (hoje - timedelta(days=2)).replace(hour=11, minute=0, second=0, microsecond=0),
        (hoje - timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0),
    ]
    historicos = [
        caixa
        for caixa in _get(api, "/caixas")
        if caixa["status"] == "fechado"
        and caixa["valor_informado"] is not None
        and datetime.fromisoformat(caixa["data_abertura"]).replace(tzinfo=None)
        <= datas[0]
        and datetime.fromisoformat(caixa["data_fechamento"]).replace(tzinfo=None)
        >= datas[1]
    ]
    if not historicos:
        pytest.skip(
            "É necessário um caixa histórico conferido que abranja as datas anteriores."
        )
    origem = min(historicos, key=lambda caixa: caixa["id"])
    resumo_origem = _get(api, f"/caixas/{origem['id']}/resumo")
    resumo_antes = _get(api, f"/caixas/{caixa_id}/resumo")
    api.config = replace(
        api.config, prefix=f"{api.config.prefix}-LOTE-{uuid4().int % 10000000000:010d}"
    )
    cliente_id = _create_cliente(api)
    produto_id, estoque_inicial = _create_produto(api)
    marker = uuid4().hex
    observacoes = f"{api.config.prefix} {marker} baixa em lote"
    vendas = []
    for quantidade in (1, 2):
        venda = api.expect(
            "POST",
            "/vendas",
            {200, 201},
            "lote.criar_venda_anterior",
            json={
                "cliente_id": cliente_id,
                "itens": [
                    {
                        "tipo": "produto",
                        "produto_id": produto_id,
                        "quantidade": quantidade,
                        "preco_unitario": 10,
                        "subtotal": quantidade * 10,
                    }
                ],
                "observacoes": observacoes,
                "tem_entrega": False,
            },
        ).json()
        vendas.append(venda["id"])
    _datar_vendas_ficticias(
        container,
        tenant_id=api.config.tenant_id,
        vendas=vendas,
        datas=datas,
        caixa_id=origem["id"],
        observacoes=observacoes,
        marker=marker,
    )
    for venda_id, data in zip(vendas, datas):
        venda = _get(api, f"/vendas/{venda_id}")
        assert venda["data_venda"][:10] == data.date().isoformat()
    estoque_apos_criacao = estoque_inicial - 3
    _verificar_estoque(api, produto_id, estoque_apos_criacao)

    api.expect(
        "POST",
        f"/clientes/{cliente_id + 2000000000}/baixar-vendas-lote",
        {404},
        "lote.cliente_incorreto",
        json={"vendas_ids": vendas, "valor_total": 12, "forma_pagamento": "PIX"},
    )
    assert all(not _pagamentos(api, venda_id)["pagamentos"] for venda_id in vendas)
    parcial = api.expect(
        "POST",
        f"/clientes/{cliente_id}/baixar-vendas-lote",
        {200},
        "lote.pix_parcial",
        json={
            "vendas_ids": list(reversed(vendas)),
            "valor_total": 12,
            "forma_pagamento": "PIX",
        },
    ).json()
    assert parcial["valor_total_baixado"] == 12
    assert parcial["total_vendas_afetadas"] == 2
    assert parcial["vendas_quitadas"][0]["id"] == vendas[0]
    assert parcial["vendas_parciais"][0]["id"] == vendas[1]
    primeira, segunda = (_pagamentos(api, venda_id) for venda_id in vendas)
    assert primeira["status"] == "finalizada" and primeira["valor_restante"] == 0
    assert segunda["status"] == "baixa_parcial" and segunda["valor_restante"] == 18
    assert [pagamento["valor"] for pagamento in primeira["pagamentos"]] == [10]
    assert [pagamento["valor"] for pagamento in segunda["pagamentos"]] == [2]
    assert all(
        pagamento["caixa_id"] == caixa_id
        for venda in (primeira, segunda)
        for pagamento in venda["pagamentos"]
    )
    _verificar_estoque(api, produto_id, estoque_apos_criacao)

    api.expect(
        "POST",
        f"/clientes/{cliente_id}/baixar-vendas-lote",
        {400},
        "lote.exceder_saldo",
        json={
            "vendas_ids": [vendas[1]],
            "valor_total": 19,
            "forma_pagamento": "Dinheiro",
        },
    )
    assert _pagamentos(api, vendas[1])["total_pago"] == 2
    quitacao = api.expect(
        "POST",
        f"/clientes/{cliente_id}/baixar-vendas-lote",
        {200},
        "lote.dinheiro_quitar",
        json={
            "vendas_ids": [vendas[1]],
            "valor_total": 18,
            "forma_pagamento": "Dinheiro",
        },
    ).json()
    assert quitacao["valor_total_baixado"] == 18
    segunda = _pagamentos(api, vendas[1])
    assert segunda["status"] == "finalizada" and segunda["valor_restante"] == 0
    assert segunda["total_pago"] == 20
    assert [
        (p["forma_pagamento"], p["valor"], p["caixa_id"]) for p in segunda["pagamentos"]
    ] == [
        ("PIX", 2, caixa_id),
        ("Dinheiro", 18, caixa_id),
    ]
    _verificar_estoque(api, produto_id, estoque_apos_criacao)

    auditoria = _get(api, f"/caixas/{caixa_id}/auditoria")
    auditadas = [venda for venda in auditoria["vendas"] if venda["venda_id"] in vendas]
    pagamentos = [p for p in auditoria["pagamentos"] if p["venda_id"] in vendas]
    movimentos = [m for m in auditoria["movimentacoes"] if m["venda_id"] in vendas]
    movimentos_originais = [
        m
        for m in _get(api, f"/caixas/{caixa_id}/movimentacoes")["movimentacoes"]
        if m["venda_id"] in vendas
    ]
    assert len(auditadas) == 2 and len(pagamentos) == 2 and len(movimentos) == 1
    assert sum(p["valor"] for p in pagamentos) == 12
    assert all(
        p["forma_pagamento"] == "PIX" and p["caixa_id"] == caixa_id for p in pagamentos
    )
    assert (
        movimentos[0]["forma_pagamento"] == "Dinheiro" and movimentos[0]["valor"] == 18
    )
    assert movimentos[0]["caixa_id"] == caixa_id
    assert len(movimentos_originais) == 1
    assert movimentos_originais[0]["forma_pagamento"] == "Dinheiro"
    assert all(venda["caixa_origem_id"] == origem["id"] for venda in auditadas)
    assert sorted(venda["valor_nesta_forma"] for venda in auditadas) == [10, 20]
    assert all(
        datetime.fromisoformat(p["data_movimento"]).date() == hoje.date()
        for p in pagamentos
    )
    assert datetime.fromisoformat(movimentos[0]["data_movimento"]).date() == hoje.date()
    resumo = auditoria["resumo"]
    assert resumo["total_recebido"] == resumo_antes["total_recebido"] + 30
    assert resumo["total_vendido"] == resumo_antes["total_vendido"]
    assert resumo["totais"]["saldo_atual"] == resumo_antes["totais"]["saldo_atual"] + 18
    detalhe_pix = [
        item
        for item in _get(api, f"/caixas/{caixa_id}/vendas?forma_pagamento=PIX")
        if item["venda_id"] in vendas
    ]
    assert (
        len(detalhe_pix) == 2
        and sum(item["valor_nesta_forma"] for item in detalhe_pix) == 12
    )
    detalhe_dinheiro = [
        item
        for item in _get(api, f"/caixas/{caixa_id}/vendas?forma_pagamento=Dinheiro")
        if item["venda_id"] in vendas
    ]
    assert len(detalhe_dinheiro) == 1 and detalhe_dinheiro[0]["valor_nesta_forma"] == 18
    resumo_origem_depois = _get(api, f"/caixas/{origem['id']}/resumo")
    assert resumo_origem_depois["total_recebido"] == resumo_origem["total_recebido"]
    assert (
        resumo_origem_depois["totais"]["saldo_atual"]
        == resumo_origem["totais"]["saldo_atual"]
    )
    assert _get(api, "/caixas/aberto")["id"] == caixa_id
