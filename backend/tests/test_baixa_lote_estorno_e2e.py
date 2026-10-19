"""Jornada financeira real, restrita ao PostgreSQL da homologação local.

Requer E2E_* da jornada básica, E2E_REUSE_CAIXA_ID e
E2E_LOCAL_SEED_CONTAINER=corepet-homolog-backend-1. O acesso ao banco abaixo
faz somente SELECTs; clientes, produtos, vendas e baixas são criados pela API.
Os registros fictícios permanecem identificados para conferência na interface.
"""

import json
import os
import subprocess
from dataclasses import replace
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4

import pytest

from tests import test_plano_basico_e2e as jornada_basica
from tests.test_plano_basico_e2e import E2EApi, _create_cliente, _create_produto

pytestmark = pytest.mark.e2e_long
api = jornada_basica.api
e2e_config = jornada_basica.e2e_config


def _get(api, path):
    return api.expect("GET", path, {200}, path).json()


def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _sum(rows, field):
    return sum((_money(row[field]) for row in rows), Decimal("0.00"))


def _snapshot(api, container, vendas, observacoes):
    """Confere os efeitos financeiros com uma transação PostgreSQL READ ONLY."""
    script = r"""
import json, os, sys
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

dados = json.load(sys.stdin)
assert os.environ.get('ENVIRONMENT') == 'staging'
url = make_url(os.environ['DATABASE_URL'])
assert url.get_backend_name() == 'postgresql' and url.database == 'corepet_homolog'
assert len(dados['vendas']) == 2 and len(set(dados['vendas'])) == 2
assert dados['observacoes'].startswith('E2E-PB-') and '-ESTORNO-' in dados['observacoes']
params = {'tenant': dados['tenant_id'], 'vendas': dados['vendas'],
          'observacoes': dados['observacoes']}
with create_engine(url).begin() as db:
    db.execute(text('SET TRANSACTION READ ONLY'))
    assert db.scalar(text('SHOW transaction_read_only')) == 'on'
    assert db.scalar(text('SELECT current_database()')) == 'corepet_homolog'
    assert db.scalar(text('SELECT name FROM tenants WHERE id::text = :tenant'), params) == 'CorePet Homologacao Local'
    assert db.scalar(text('SELECT count(*) FROM vendas WHERE tenant_id::text = :tenant AND id = ANY(:vendas) AND observacoes = :observacoes'), params) == 2
    consultas = {
        'pagamentos': 'SELECT id, venda_id, valor, baixa_lote_id, caixa_id FROM venda_pagamentos WHERE tenant_id::text = :tenant AND venda_id = ANY(:vendas) ORDER BY id',
        'contas': 'SELECT id, venda_id, valor_final, valor_recebido, status FROM contas_receber WHERE tenant_id::text = :tenant AND venda_id = ANY(:vendas) ORDER BY id',
        'recibos': 'SELECT r.id, r.conta_receber_id, r.valor_recebido FROM recebimentos r JOIN contas_receber c ON c.id=r.conta_receber_id AND c.tenant_id=r.tenant_id WHERE r.tenant_id::text = :tenant AND c.venda_id = ANY(:vendas) ORDER BY r.id',
        'fluxos': "SELECT f.id, f.origem_id, f.valor, f.status FROM fluxo_caixa f JOIN contas_receber c ON c.id=f.origem_id AND c.tenant_id=f.tenant_id WHERE f.tenant_id::text = :tenant AND f.origem_tipo='conta_receber' AND c.venda_id = ANY(:vendas) ORDER BY f.id",
        'movimentos': 'SELECT id, venda_id, caixa_id, tipo, valor FROM movimentacoes_caixa WHERE tenant_id::text = :tenant AND venda_id = ANY(:vendas) ORDER BY id',
        'itens': 'SELECT id, lote_id, venda_id, pagamento_id, pagamento_estorno_id, efeitos FROM vendas_baixas_lote_itens WHERE tenant_id::text = :tenant AND venda_id = ANY(:vendas) ORDER BY id',
        'auditoria': "SELECT id, action, entity_id FROM audit_logs WHERE tenant_id::text = :tenant AND entity_type='vendas_baixas_lotes' AND entity_id IN (SELECT lote_id FROM vendas_baixas_lote_itens WHERE tenant_id::text = :tenant AND venda_id=ANY(:vendas)) ORDER BY id",
    }
    resultado = {nome: [dict(row) for row in db.execute(text(sql), params).mappings()] for nome, sql in consultas.items()}
print(json.dumps(resultado, default=str))
"""
    result = subprocess.run(
        ["docker", "exec", "-i", container, "python", "-c", script],
        input=json.dumps(
            {
                "tenant_id": api.config.tenant_id,
                "vendas": vendas,
                "observacoes": observacoes,
            }
        ),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout)


def _assert_saldos(snapshot, recebido, previsto, pagamentos, recibos):
    assert len(snapshot["pagamentos"]) == pagamentos
    assert len(snapshot["recibos"]) == recibos
    assert _sum(snapshot["pagamentos"], "valor") == _money(recebido)
    assert _sum(snapshot["recibos"], "valor_recebido") == _money(recebido)
    assert _sum(snapshot["contas"], "valor_recebido") == _money(recebido)
    assert _sum(
        [f for f in snapshot["fluxos"] if f["status"] == "realizado"], "valor"
    ) == _money(recebido)
    assert _sum(
        [f for f in snapshot["fluxos"] if f["status"] == "previsto"], "valor"
    ) == _money(previsto)


def _assert_caixa(api, caixa_id, antes, recebido, dinheiro):
    resumo = _get(api, f"/caixas/{caixa_id}/resumo")
    assert _money(resumo["total_recebido"]) == _money(antes["total_recebido"]) + _money(
        recebido
    )
    assert _money(resumo["totais"]["saldo_atual"]) == _money(
        antes["totais"]["saldo_atual"]
    ) + _money(dinheiro)


@pytest.mark.parametrize("forma", ["Dinheiro", "PIX"])
def test_baixa_errada_estorno_integral_e_nova_baixa_correta(api: E2EApi, forma):
    if urlparse(api.config.base_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.skip("Jornada permitida somente na homologação local.")
    me = _get(api, "/auth/me-multitenant")
    if me["tenant"]["name"] != "CorePet Homologacao Local":
        pytest.skip("Jornada exige a empresa fictícia CorePet Homologacao Local.")
    caixa_indicado = os.getenv("E2E_REUSE_CAIXA_ID")
    container = os.getenv("E2E_LOCAL_SEED_CONTAINER")
    if not caixa_indicado or container != "corepet-homolog-backend-1":
        pytest.skip("Indique o caixa aberto e o container explícito da homologação.")
    caixa = _get(api, "/caixas/aberto")
    assert caixa and str(caixa["id"]) == caixa_indicado and caixa["status"] == "aberto"
    caixa_id = caixa["id"]
    api.config = replace(
        api.config,
        prefix=f"E2E-PB-ESTORNO-{uuid4().int % 100000000000000:014d}",
    )
    cliente_id = _create_cliente(api)
    produto_id, estoque_inicial = _create_produto(api)
    observacoes = f"{api.config.prefix} baixa errada, estorno e correção {forma}"
    vendas = []
    for quantidade in (1, 2):
        venda = api.expect(
            "POST",
            "/vendas",
            {200, 201},
            "estorno.criar_venda_ficticia",
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
    estoque_esperado = estoque_inicial - 3
    assert _money(_get(api, f"/produtos/{produto_id}")["estoque_atual"]) == _money(
        estoque_esperado
    )
    antes = _get(api, f"/caixas/{caixa_id}/resumo")
    snapshot_inicial = _snapshot(api, container, vendas, observacoes)
    assert not snapshot_inicial["pagamentos"]
    payload = {
        "vendas_ids": list(reversed(vendas)),
        "valor_total": 12,
        "forma_pagamento": forma,
        "request_id": str(uuid4()),
        "observacoes": observacoes,
    }
    path = f"/clientes/{cliente_id}/baixar-vendas-lote"
    baixa = api.expect("POST", path, {200}, "estorno.baixa_errada", json=payload).json()
    lote_id = baixa["lote_id"]
    assert baixa["valor_total_baixado"] == 12 and baixa["total_vendas_afetadas"] == 2
    assert (
        api.expect("POST", path, {200}, "estorno.repetir_baixa", json=payload).json()
        == baixa
    )
    historico_path = f"/clientes/{cliente_id}/baixas-lote"
    historico = _get(api, historico_path)
    assert historico["total"] == 1
    assert historico["itens"][0]["id"] == lote_id
    assert [item["valor_baixado"] for item in historico["itens"][0]["vendas"]] == [
        10,
        2,
    ]
    snapshot_baixa = _snapshot(api, container, vendas, observacoes)
    _assert_saldos(snapshot_baixa, 12, 18, 2, 2)
    _assert_caixa(api, caixa_id, antes, 12, 12 if forma == "Dinheiro" else 0)
    pagamento_id = snapshot_baixa["pagamentos"][0]["id"]
    api.expect(
        "DELETE",
        f"/vendas/pagamentos/{pagamento_id}",
        {409},
        "estorno.bloquear_exclusao_rateio",
    )
    motivo = f"{api.config.prefix}: valor informado incorretamente"
    estorno_path = f"/clientes/{cliente_id}/baixas-lote/{lote_id}/estornar"
    api.expect(
        "POST", estorno_path, {422}, "estorno.motivo_invalido", json={"motivo": "x"}
    )
    estornado = api.expect(
        "POST", estorno_path, {200}, "estorno.integral", json={"motivo": motivo}
    ).json()
    assert estornado["status"] == "estornado" and estornado["motivo_estorno"] == motivo
    assert estornado["estornado_em"] and estornado["estornado_por_nome"]
    assert (
        api.expect(
            "POST", estorno_path, {200}, "estorno.repetir", json={"motivo": motivo}
        ).json()
        == estornado
    )
    snapshot_estorno = _snapshot(api, container, vendas, observacoes)
    _assert_saldos(snapshot_estorno, 0, 30, 4, 4)
    assert snapshot_estorno["pagamentos"][:2] == snapshot_baixa["pagamentos"]
    assert all(item["pagamento_estorno_id"] for item in snapshot_estorno["itens"])
    assert (
        len(
            [
                a
                for a in snapshot_estorno["auditoria"]
                if a["action"] == "estornar_baixa_lote"
            ]
        )
        == 1
    )
    _assert_caixa(api, caixa_id, antes, 0, 0)
    for venda_id, total in zip(vendas, (10, 20)):
        pagamento = _get(api, f"/vendas/{venda_id}/pagamentos")
        assert pagamento["status"] == "aberta"
        assert pagamento["total_pago"] == 0 and pagamento["valor_restante"] == total
    assert _money(_get(api, f"/produtos/{produto_id}")["estoque_atual"]) == _money(
        estoque_esperado
    )
    correta = {**payload, "valor_total": 30, "request_id": str(uuid4())}
    nova = api.expect("POST", path, {200}, "estorno.baixa_correta", json=correta).json()
    assert nova["lote_id"] != lote_id and nova["total_vendas_afetadas"] == 2
    assert nova["valor_total_baixado"] == 30 and not nova["vendas_parciais"]
    snapshot_final = _snapshot(api, container, vendas, observacoes)
    _assert_saldos(snapshot_final, 30, 0, 6, 6)
    assert snapshot_final["pagamentos"][:4] == snapshot_estorno["pagamentos"]
    assert len(snapshot_final["itens"]) == 4
    assert len(snapshot_final["auditoria"]) == 3
    movimentos = snapshot_final["movimentos"]
    dinheiro_liquido = sum(
        (
            _money(m["valor"]) * (-1 if m["tipo"] == "devolucao" else 1)
            for m in movimentos
        ),
        Decimal("0.00"),
    )
    assert dinheiro_liquido == _money(30 if forma == "Dinheiro" else 0)
    _assert_caixa(api, caixa_id, antes, 30, 30 if forma == "Dinheiro" else 0)
    for venda_id, total in zip(vendas, (10, 20)):
        pagamento = _get(api, f"/vendas/{venda_id}/pagamentos")
        assert pagamento["status"] == "finalizada"
        assert pagamento["total_pago"] == total and pagamento["valor_restante"] == 0
    assert _money(_get(api, f"/produtos/{produto_id}")["estoque_atual"]) == _money(
        estoque_esperado
    )
    historico = _get(api, historico_path)
    assert historico["total"] == 2
    assert {lote["id"]: lote["status"] for lote in historico["itens"]} == {
        lote_id: "estornado",
        nova["lote_id"]: "confirmado",
    }
    print(
        json.dumps(
            {
                "jornada": api.config.prefix,
                "forma": forma,
                "cliente_id": cliente_id,
                "produto_id": produto_id,
                "vendas": vendas,
                "caixa_id": caixa_id,
                "lote_estornado": lote_id,
                "lote_correto": nova["lote_id"],
                "recebido_liquido": 30,
                "estoque_final": estoque_esperado,
            }
        )
    )
