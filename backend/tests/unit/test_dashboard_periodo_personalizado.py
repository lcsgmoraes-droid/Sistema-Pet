"""Janela personalizada real das quatro consultas comerciais do dashboard."""

from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.schema import CreateTable

import app.dashboard_routes as dashboard
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro_models import ContaPagar
from app import produto_identidade_models  # noqa: F401 - resolve FK do catálogo
from app.produtos_models import Produto
from app.grupo_comercial_models import (
    GrupoComercial,
    GrupoComercialMembro,
    GrupoComercialEstoqueCompartilhado,
)
from app.veterinario_models import VetPartnerLink
from app.vendas_models import Venda, VendaItem, VendaPagamento
from tests.unit.test_caixa_recebimentos_auditoria import (  # noqa: F401
    caixa_session,
    recebimentos,
)
from tests.unit.test_faturamento_superficies import cenario  # noqa: F401


ENDPOINTS = (
    "/dashboard/resumo",
    "/dashboard/entradas-saidas",
    "/dashboard/vendas-por-dia",
    "/dashboard/top-produtos",
)


def _app(db, auth):
    app = FastAPI()
    app.include_router(dashboard.router)
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_current_user_and_tenant] = lambda: auth
    return app


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize(
    "params, trecho",
    [
        ({"data_inicio": "2026-10-01"}, "Informe data_inicio e data_fim"),
        ({"data_fim": "2026-10-01"}, "Informe data_inicio e data_fim"),
        ({"data_inicio": "2026-02-30", "data_fim": "2026-03-01"}, "data_inicio"),
        ({"data_inicio": "20261001", "data_fim": "2026-10-02"}, "AAAA-MM-DD"),
        ({"data_inicio": "2026-10-01", "data_fim": ""}, "data_fim"),
        (
            {"data_inicio": "2026-10-03", "data_fim": "2026-10-01"},
            "anterior ou igual",
        ),
        ({"data_inicio": "2026-01-01", "data_fim": "2026-04-01"}, "90 dias"),
        (
            {"data_inicio": "9999-12-31", "data_fim": "9999-12-31"},
            "fora do intervalo",
        ),
    ],
)
def test_filtro_invalido_retorna_400_antes_de_qualquer_consulta(
    endpoint, params, trecho
):
    class SemConsulta:
        def query(self, *_):
            pytest.fail("Filtro inválido chegou ao banco")

    with TestClient(_app(SemConsulta(), (SimpleNamespace(id=91), uuid4()))) as client:
        resposta = client.get(endpoint, params=params)
    assert resposta.status_code == 400
    assert trecho in resposta.json()["detail"]


def test_intervalo_personalizado_90_dias_inclusivos_e_limite_exclusivo():
    inicio, fim = dashboard._intervalo_dashboard(30, "2026-01-01", "2026-03-31")
    assert inicio == datetime(2026, 1, 1)
    assert fim == datetime(2026, 4, 1)
    assert (fim - inicio).days == 90
    with pytest.raises(HTTPException) as erro:
        dashboard._intervalo_dashboard(30, "2026-01-01", "2026-04-01")
    assert erro.value.status_code == 400


def test_dia_unico_e_periodo_futuro_nao_dependem_da_data_atual():
    assert dashboard._intervalo_dashboard(30, "2030-10-01", "2030-10-01") == (
        datetime(2030, 10, 1),
        datetime(2030, 10, 2),
    )


def test_atalho_legado_366_dias_permanece_disponivel():
    inicio, fim = dashboard._intervalo_dashboard(366, agora=datetime(2026, 10, 22, 23))
    assert (fim - inicio).days == 366
    assert fim == datetime(2026, 10, 23)


@pytest.fixture
def periodo_cenario(request, tenant_context):
    caso = request.getfixturevalue("cenario")
    db = caso.db
    engine = db.get_bind()
    # Mesmo schema descartável da fixture: não depender do catálogo público.
    with engine.begin() as conn:
        conn.execute(CreateTable(Produto.__table__, include_foreign_key_constraints=[]))
        if engine.dialect.name == "postgresql":
            for model in (
                VetPartnerLink,
                GrupoComercial,
                GrupoComercialMembro,
                GrupoComercialEstoqueCompartilhado,
            ):
                conn.execute(
                    CreateTable(model.__table__, include_foreign_key_constraints=[])
                )
    produto = Produto(
        tenant_id=caso.auth[1], codigo="PERIODO", nome="Produto da janela", user_id=91
    )
    db.add(produto)
    db.flush()
    for numero, data, valor, tenant, status in [
        ("ANTES", datetime(2026, 9, 30, 23, 59, 59), 900, caso.auth[1], "finalizada"),
        ("INICIO", datetime(2026, 10, 1), 20, caso.auth[1], "finalizada"),
        (
            "FIM",
            datetime(2026, 10, 2, 23, 59, 59, 999999),
            30,
            caso.auth[1],
            "finalizada",
        ),
        ("DEPOIS", datetime(2026, 10, 3), 800, caso.auth[1], "finalizada"),
        ("OUTRO-TENANT", datetime(2026, 10, 1), 700, uuid4(), "finalizada"),
        ("CANCELADA", datetime(2026, 10, 1), 600, caso.auth[1], "cancelada"),
    ]:
        tenant_context(tenant)
        venda = Venda(
            tenant_id=tenant,
            numero_venda=numero,
            user_id=91,
            vendedor_id=91,
            subtotal=valor,
            total=valor,
            status=status,
            data_venda=data,
            canal="loja_fisica",
        )
        db.add(venda)
        db.flush()
        db.add(
            VendaPagamento(
                tenant_id=tenant,
                venda_id=venda.id,
                forma_pagamento="PIX",
                valor=valor,
                status="confirmado",
                data_pagamento=data,
            )
        )
        db.add(
            VendaItem(
                tenant_id=tenant,
                venda_id=venda.id,
                produto_id=produto.id,
                tipo="produto",
                quantidade=1,
                preco_unitario=valor,
                subtotal=valor,
            )
        )
        db.flush()
    for numero, dia, valor, tenant in [
        ("ANTES", date(2026, 9, 30), 900, caso.auth[1]),
        ("INICIO", date(2026, 10, 1), 4, caso.auth[1]),
        ("FIM", date(2026, 10, 2), 6, caso.auth[1]),
        ("DEPOIS", date(2026, 10, 3), 800, caso.auth[1]),
        ("OUTRO-TENANT", date(2026, 10, 1), 700, uuid4()),
    ]:
        db.flush()
        tenant_context(tenant)
        db.add(
            ContaPagar(
                tenant_id=tenant,
                user_id=91,
                descricao=numero,
                valor_original=valor,
                valor_final=valor,
                valor_pago=valor,
                data_emissao=dia,
                data_vencimento=dia,
                data_pagamento=dia,
                status="pago",
                dre_subcategoria_id=1,
            )
        )
    db.flush()
    tenant_context(caso.auth[1])
    db.expire_all()
    return caso


@pytest.mark.asyncio
async def test_endpoints_usam_mesma_janela_historica_com_limites_e_tenant(
    periodo_cenario,
):
    caso = periodo_cenario
    params = {"data_inicio": "2026-10-01", "data_fim": "2026-10-02", "periodo_dias": 90}
    async with AsyncClient(
        transport=ASGITransport(app=_app(caso.db, caso.auth)),
        base_url="http://dev.test",
    ) as client:
        respostas = [
            await client.get(endpoint, params=params) for endpoint in ENDPOINTS
        ]
        vazio = await client.get(
            "/dashboard/resumo",
            params={"data_inicio": "2026-09-28", "data_fim": "2026-09-29"},
        )
    assert [resposta.status_code for resposta in respostas] == [200] * 4
    resumo, fluxo, vendas, produtos = [resposta.json() for resposta in respostas]
    assert resumo["periodo_dias"] == 2
    assert resumo["data_inicio"] == "2026-10-01"
    assert resumo["data_fim"] == "2026-10-02"
    assert resumo["vendas_periodo"]["quantidade"] == 2
    assert resumo["vendas_periodo"]["faturamento_liquido"] == 50
    assert resumo["fluxo_periodo"]["entradas"] == 50
    assert resumo["fluxo_periodo"]["saidas"] == 10
    assert {
        venda["numero_venda"] for venda in resumo["composicao_vendas"]["detalhes"]
    } == {"INICIO", "FIM"}
    assert fluxo == [
        {"data": "2026-10-01", "entradas": 20, "saidas": 4},
        {"data": "2026-10-02", "entradas": 30, "saidas": 6},
    ]
    assert vendas == [
        {"data": "2026-10-01", "quantidade": 1, "valor_total": 20},
        {"data": "2026-10-02", "quantidade": 1, "valor_total": 30},
    ]
    assert produtos == [
        {"nome": "Produto da janela", "quantidade_vendida": 2, "receita_total": 50}
    ]
    assert vazio.status_code == 200
    assert vazio.json()["vendas_periodo"]["quantidade"] == 0
    for posicao_atual in ("saldo_atual", "contas_receber", "contas_pagar"):
        assert vazio.json()[posicao_atual] == resumo[posicao_atual]


@pytest.mark.asyncio
async def test_dias_sem_venda_sao_preenchidos_no_intervalo_personalizado(
    periodo_cenario,
):
    caso = periodo_cenario
    for endpoint in ENDPOINTS[1:3]:
        async with AsyncClient(
            transport=ASGITransport(app=_app(caso.db, caso.auth)),
            base_url="http://dev.test",
        ) as client:
            resposta = await client.get(
                endpoint, params={"data_inicio": "2026-09-28", "data_fim": "2026-09-29"}
            )
        assert resposta.status_code == 200
        dias = resposta.json()
        assert [dia["data"] for dia in dias] == ["2026-09-28", "2026-09-29"]
        assert all(
            valor == 0
            for dia in dias
            for campo, valor in dia.items()
            if campo != "data"
        )
