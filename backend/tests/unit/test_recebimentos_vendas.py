"""Provas com banco: períodos, múltiplas fontes e isolamento dos recebimentos."""

from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user_and_tenant
from app.conciliacao_recebimento_models import ConciliacaoRecebimento
from app.db import get_session
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.empresa_config_routes import router as config_router
from app.financeiro.recebimentos_vendas_routes import router
from app.financeiro.recebimentos_vendas_service import montar_relatorio_recebimentos
from app.financeiro.visao_comercial import obter_visao_comercial
from app.financeiro_models import (
    ContaReceber,
    FormaPagamento,
    LancamentoManual,
    Recebimento,
)
from app.vendas_models import Venda
from app.models import AuditLog, Cliente

AGO = (date(2026, 8, 1), date(2026, 8, 31))
SET = (date(2026, 9, 1), date(2026, 9, 30))


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for modelo in (
        Cliente,
        Venda,
        ContaReceber,
        Recebimento,
        FormaPagamento,
        LancamentoManual,
        ConciliacaoRecebimento,
        EmpresaConfigGeral,
        AuditLog,
    ):
        modelo.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def dados(db_session, tenant_context):
    tenant = uuid4()
    tenant_context(tenant)
    ids = {"venda": 10000, "conta": 10000, "baixa": 10000}

    def inserir(modelo, **valores):
        valores.setdefault("tenant_id", tenant)
        db_session.execute(modelo.__table__.insert().values(**valores))

    def venda(data=datetime(2026, 7, 10), total=1000, **extras):
        ids["venda"] += 1
        ident = ids["venda"]
        inserir(
            Venda,
            id=ident,
            numero_venda=f"TEST-{ident}",
            vendedor_id=1,
            user_id=1,
            subtotal=total,
            total=total,
            data_venda=data,
            status=extras.pop("status", "finalizada"),
            **extras,
        )
        return ident

    def conta(venda_id, **extras):
        ids["conta"] += 1
        ident = ids["conta"]
        valores = dict(
            descricao="Venda de teste",
            dre_subcategoria_id=1,
            canal="loja_fisica",
            valor_original=1000,
            valor_final=1000,
            valor_recebido=0,
            data_emissao=date(2026, 7, 10),
            data_vencimento=date(2026, 8, 10),
            status="pendente",
            user_id=1,
        )
        valores.update(extras)
        inserir(ContaReceber, id=ident, venda_id=venda_id, **valores)
        return ident

    def baixa(conta_id, valor=1000, data=date(2026, 8, 10), **extras):
        ids["baixa"] += 1
        inserir(
            Recebimento,
            id=ids["baixa"],
            conta_receber_id=conta_id,
            valor_recebido=valor,
            data_recebimento=data,
            user_id=1,
            **extras,
        )

    def relatorio(periodo=AGO, **extras):
        db_session.expire_all()
        return montar_relatorio_recebimentos(db_session, tenant, *periodo, **extras)

    return SimpleNamespace(
        tenant=tenant,
        db=db_session,
        inserir=inserir,
        venda=venda,
        conta=conta,
        baixa=baixa,
        relatorio=relatorio,
    )


def test_venda_nao_recebida_e_pagamento_de_mes_anterior(dados):
    dados.conta(dados.venda(datetime(2026, 8, 5)))
    assert dados.relatorio()["resumo"]["total"] == 0
    dados.baixa(dados.conta(dados.venda()))
    resultado = dados.relatorio()
    assert resultado["resumo"]["total"] == 1000
    assert resultado["movimentos"][0]["data_venda"] == "2026-07-10"
    assert resultado["movimentos"][0]["data_recebimento"] == "2026-08-10"
    assert sum(d["valor"] for d in resultado["por_dia"]) == 1000


def test_parciais_respeitam_mes_sem_repetir_total_da_conta(dados):
    conta = dados.conta(
        dados.venda(),
        status="recebido",
        valor_recebido=1000,
        data_recebimento=date(2026, 9, 10),
    )
    dados.baixa(conta, 300)
    dados.baixa(conta, 700, date(2026, 9, 10))
    assert dados.relatorio()["resumo"]["total"] == 300
    assert dados.relatorio(SET)["resumo"]["total"] == 700
    assert len(dados.relatorio(SET)["movimentos"]) == 1


def test_limites_do_mes_e_centavos(dados):
    conta = dados.conta(dados.venda())
    for data, valor in [
        (date(2026, 7, 31), 100),
        (AGO[0], 0.1),
        (AGO[1], 0.2),
        (SET[0], 200),
    ]:
        dados.baixa(conta, valor, data)
    assert dados.relatorio()["resumo"]["total"] == 0.3


def test_conta_legada_exige_data_real_e_nao_duplica_baixas_de_outro_mes(dados):
    dados.conta(
        dados.venda(), status="recebido", valor_recebido=450, data_recebimento=AGO[0]
    )
    dados.conta(dados.venda(), status="recebido", valor_recebido=999)
    conta = dados.conta(
        dados.venda(), status="recebido", valor_recebido=200, data_recebimento=AGO[0]
    )
    dados.baixa(conta, 200, SET[0])
    assert dados.relatorio()["resumo"]["total"] == 450


def test_conciliacao_antecipada_contada_uma_vez_e_na_data_confirmada(dados):
    venda = dados.venda(total=1000)
    dados.inserir(
        ConciliacaoRecebimento,
        id=10000,
        nsu="TEST",
        data_recebimento=SET[0],
        valor=950,
        tipo_recebimento="antecipacao",
        validado=True,
        amarrado=True,
        venda_id=venda,
    )
    for _ in range(2):
        conta = dados.conta(
            venda,
            valor_original=500,
            valor_final=500,
            valor_recebido=500,
            data_recebimento=SET[0],
            status="recebido",
            conciliacao_recebimento_id=10000,
        )
        dados.baixa(conta, 500, AGO[0])
    assert dados.relatorio()["resumo"]["total"] == 0
    assert dados.relatorio(SET)["resumo"]["total"] == 950
    assert len(dados.relatorio(SET)["movimentos"]) == 1
    dados.inserir(
        ConciliacaoRecebimento,
        id=10001,
        nsu="SEM-CONFIRMACAO",
        data_recebimento=SET[0],
        valor=999,
        tipo_recebimento="parcela_individual",
        validado=False,
        amarrado=False,
        venda_id=venda,
    )
    assert dados.relatorio(SET)["resumo"]["total"] == 950


def test_devolucao_em_outro_mes_preserva_entrada_e_credito_nao_soma(dados):
    venda = dados.venda(status="devolvida_total")
    dados.baixa(dados.conta(venda), 1000)
    dados.inserir(
        LancamentoManual,
        id=10000,
        tipo="saida",
        valor=1000,
        descricao="Devolução teste",
        data_lancamento=SET[0],
        status="realizado",
        documento=f"DEVOLUCAO-{venda}",
        user_id=1,
    )
    dados.inserir(
        FormaPagamento,
        id=10000,
        nome="Crédito do Cliente",
        tipo="credito_cliente",
        user_id=1,
    )
    dados.baixa(dados.conta(dados.venda(), forma_pagamento_id=10000), 400)
    assert dados.relatorio()["resumo"]["total"] == 1000
    assert dados.relatorio(SET)["resumo"] == {
        "recebimentos": 0,
        "devolucoes": 1000,
        "total": -1000,
    }


def test_cancelamento_transferencia_e_canal(dados):
    dados.baixa(dados.conta(dados.venda(status="cancelada")), 200)
    dados.baixa(dados.conta(dados.venda(canal="app")), 400)
    dados.inserir(
        LancamentoManual,
        id=10000,
        tipo="entrada",
        valor=999,
        descricao="Transferência",
        data_lancamento=AGO[0],
        status="realizado",
        documento="TRANSFERENCIA-1",
        user_id=1,
    )
    assert dados.relatorio()["resumo"]["total"] == 400
    assert dados.relatorio(canal="loja_fisica")["resumo"]["total"] == 0


def test_isolamento_inclusive_vinculo_inconsistente(dados):
    outra = uuid4()
    propria = dados.venda()
    estrangeira = dados.venda(tenant_id=outra)
    dados.baixa(dados.conta(propria), 123)
    dados.baixa(dados.conta(estrangeira), 888)
    dados.baixa(dados.conta(propria, tenant_id=outra), 999)
    dados.baixa(dados.conta(propria), 777, tenant_id=outra)
    assert dados.relatorio()["resumo"]["total"] == 123


@pytest.fixture
def http(dados, monkeypatch):
    app = FastAPI()
    app.include_router(config_router)
    app.include_router(router, prefix="/relatorios")
    app.dependency_overrides[get_session] = lambda: dados.db
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=1),
        dados.tenant,
    )
    monkeypatch.setattr(
        "app.security.permissions_decorator.check_permission", lambda *a, **k: True
    )
    return TestClient(app)


def test_config_padrao_persistencia_isolamento_e_reversao(http, dados):
    assert http.get("/empresa/config/visao-comercial").json() == {
        "visao_comercial": "venda"
    }
    dados.inserir(EmpresaConfigGeral, id=10000)
    assert (
        http.put(
            "/empresa/config/", json={"visao_comercial": "recebimento"}
        ).status_code
        == 200
    )
    assert http.get("/empresa/config/visao-comercial").json() == {
        "visao_comercial": "recebimento"
    }
    assert obter_visao_comercial(dados.db, uuid4()) == "venda"
    assert (
        http.put("/empresa/config/", json={"visao_comercial": "venda"}).status_code
        == 200
    )
    assert obter_visao_comercial(dados.db, dados.tenant) == "venda"
    assert (
        http.put("/empresa/config/", json={"visao_comercial": "invalida"}).status_code
        == 422
    )
    assert (
        http.put("/empresa/config/", json={"visao_comercial": None}).status_code == 422
    )


def test_sem_permissao_nao_altera_preferencia(http, monkeypatch):
    def negar(*args, **kwargs):
        raise HTTPException(403, "Sem permissão")

    monkeypatch.setattr("app.security.permissions_decorator.check_permission", negar)
    assert http.get("/empresa/config/visao-comercial").status_code == 200
    assert (
        http.put(
            "/empresa/config/", json={"visao_comercial": "recebimento"}
        ).status_code
        == 403
    )


def test_http_periodos_e_pdf(http, dados):
    dados.baixa(dados.conta(dados.venda()), 1234.56)
    params = {"data_inicio": "2026-08-01", "data_fim": "2026-08-31"}
    response = http.get("/relatorios/vendas/recebimentos", params=params)
    assert response.status_code == 200
    assert response.json()["resumo"]["total"] == 1234.56
    pdf = http.get("/relatorios/vendas/recebimentos/pdf", params=params)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert (
        http.get(
            "/relatorios/vendas/recebimentos",
            params={**params, "data_fim": "2026-07-01"},
        ).status_code
        == 400
    )
    assert (
        http.get(
            "/relatorios/vendas/recebimentos",
            params={**params, "data_fim": "2028-07-01"},
        ).status_code
        == 400
    )
    assert http.get("/relatorios/vendas/recebimentos").status_code == 422


@pytest.mark.parametrize("sufixo", ["", "/pdf"])
def test_sem_permissao_financeira_nao_consulta_nem_exporta(http, monkeypatch, sufixo):
    def negar(db, user_id, permission, *args, **kwargs):
        assert permission == "relatorios.financeiro"
        raise HTTPException(403, "Sem permissão financeira")

    monkeypatch.setattr("app.security.permissions_decorator.check_permission", negar)
    response = http.get(
        "/relatorios/vendas/recebimentos" + sufixo,
        params={"data_inicio": "2026-08-01", "data_fim": "2026-08-31"},
    )
    assert response.status_code == 403
