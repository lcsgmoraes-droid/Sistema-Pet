from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import caixa_models, produto_identidade_models  # noqa: F401
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.financeiro_models import ContaReceber
from app.models import Cliente, User
from app.produtos import relatorios_routes as rotas
from app.produtos_models import Categoria, EstoqueMovimentacao, Marca, Produto
from app.vendas_models import Venda, VendaItem


@pytest.fixture
def relatorio(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for model in (
        Cliente,
        User,
        Categoria,
        Marca,
        Produto,
        Venda,
        VendaItem,
        EstoqueMovimentacao,
        ContaReceber,
    ):
        model.__table__.create(engine)
    db = Session(engine)
    tenant, outro_tenant = uuid4(), uuid4()
    db.execute(
        Produto.__table__.insert().values(
            id=1,
            tenant_id=tenant,
            nome="Ração granel",
            codigo="RACAO",
            user_id=1,
            unidade="KG",
            estoque_atual=60,
        )
    )
    db.commit()
    contador = 0

    def venda(quantidade, **extra):
        nonlocal contador
        contador += 1
        valores = dict(
            id=contador,
            tenant_id=tenant,
            numero_venda=f"VEN-{contador}",
            vendedor_id=1,
            user_id=1,
            subtotal=Decimal(str(quantidade)) * 10,
            total=Decimal(str(quantidade)) * 10,
            status="finalizada",
            data_venda=datetime(2026, 10, 24, 12) + timedelta(minutes=contador),
        )
        valores.update(extra)
        db.execute(Venda.__table__.insert().values(**valores))
        db.execute(
            VendaItem.__table__.insert().values(
                id=contador,
                venda_id=contador,
                tenant_id=valores["tenant_id"],
                tipo="produto",
                produto_id=1,
                quantidade=Decimal(str(quantidade)),
                preco_unitario=10,
                subtotal=Decimal(str(quantidade)) * 10,
            )
        )
        db.commit()
        return contador

    def movimento(quantidade, **extra):
        nonlocal contador
        contador += 1
        valores = dict(
            id=contador,
            tenant_id=tenant,
            produto_id=1,
            user_id=1,
            quantidade=quantidade,
            quantidade_nova=60,
            tipo="saida",
            motivo="ajuste",
            valor_total=abs(quantidade) * 10,
            created_at=datetime(2026, 10, 24, 12) + timedelta(minutes=contador),
        )
        valores.update(extra)
        db.execute(EstoqueMovimentacao.__table__.insert().values(**valores))
        db.commit()
        return contador

    monkeypatch.setattr(rotas, "get_all_accessible_tenant_ids", lambda *_: [tenant])
    permissoes = []
    monkeypatch.setattr(
        "app.security.permissions_decorator.check_permission",
        lambda *a, **k: permissoes.append(a[2]),
    )
    app = FastAPI()
    app.include_router(rotas.router, prefix="/produtos")
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=1),
        tenant,
    )
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            venda=venda,
            movimento=movimento,
            db=db,
            tenant=tenant,
            outro_tenant=outro_tenant,
            permissoes=permissoes,
        )
    db.close()
    engine.dispose()


def consultar(relatorio, rota="produto-vendas", **params):
    resposta = relatorio.client.get(
        f"/produtos/relatorio/{rota}",
        params={
            "produto_id": 1,
            "data_inicio": "2026-10-01",
            "data_fim": "2026-10-24",
            **params,
        },
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


@pytest.mark.parametrize(
    "operador,esperado",
    [
        ("abaixo_de", [0.999, 0.5]),
        ("igual_a", [1.0]),
        ("acima_de", [2.0, 1.001]),
    ],
)
def test_vendas_limites_estritos_decimal_e_metricas_coerentes(
    relatorio, operador, esperado
):
    for quantidade in (0.5, 0.999, 1, 1.001, 2):
        relatorio.venda(quantidade)
    # Não podem aparecer em histórico, última venda ou agregações.
    relatorio.venda(0.5, status="cancelada")
    relatorio.venda(2, status="devolvida")
    relatorio.venda(2, tenant_id=relatorio.outro_tenant)
    dados = consultar(relatorio, quantidade_operador=operador, quantidade_valor="1")
    assert [item["quantidade"] for item in dados["historico_vendas"]] == esperado
    assert dados["historico_total"] == len(esperado)
    assert dados["resumo"]["ultima_venda"]["quantidade"] == esperado[0]
    assert dados["produto"]["unidade"] == "KG"
    assert dados["produto"]["estoque_atual"] == 60
    for janela in dados["janelas"]:
        assert janela["quantidade_vendida"] == pytest.approx(sum(esperado))
        assert janela["numero_vendas"] == len(esperado)
        assert janela["valor_vendido"] == pytest.approx(round(sum(esperado) * 10, 2))
    assert dados["curva_30_dias"][-1]["quantidade"] == pytest.approx(sum(esperado))
    assert dados["resumo"]["media_diaria_30"] == round(sum(esperado) / 30, 2)
    assert set(relatorio.permissoes) == {"produtos.visualizar"}


def test_historico_paginado_e_sem_resultados_nao_reusa_ultima_venda(relatorio):
    for quantidade in (0.125, 0.375, 0.625, 1):
        relatorio.venda(quantidade)
    parametros = dict(
        quantidade_operador="abaixo_de", quantidade_valor="1", page_size=1
    )
    primeira = consultar(relatorio, **parametros)
    segunda = consultar(relatorio, page=2, **parametros)
    assert primeira["historico_vendas"][0]["quantidade"] == 0.625
    assert segunda["historico_vendas"][0]["quantidade"] == 0.375
    assert primeira["historico_pages"] == primeira["historico_total"] == 3
    assert primeira["janelas"] == segunda["janelas"]
    vazio = consultar(relatorio, quantidade_operador="acima_de", quantidade_valor="2")
    assert vazio["historico_total"] == 0
    assert vazio["historico_vendas"] == []
    assert vazio["resumo"]["ultima_venda"] is None
    assert vazio["resumo"]["cobertura_estimada_dias"] is None
    assert all(item["quantidade"] == 0 for item in vazio["curva_30_dias"])
    assert consultar(relatorio)["historico_total"] == 4


def test_comparacao_e_por_item_vendido_inclusive_itens_da_mesma_venda(relatorio):
    venda_id = relatorio.venda(0.6)
    relatorio.db.execute(
        VendaItem.__table__.insert().values(
            id=100,
            venda_id=venda_id,
            tenant_id=relatorio.tenant,
            tipo="produto",
            produto_id=1,
            quantidade=Decimal("0.600"),
            preco_unitario=10,
            subtotal=6,
        )
    )
    relatorio.db.commit()
    abaixo = consultar(relatorio, quantidade_operador="abaixo_de", quantidade_valor="1")
    assert abaixo["historico_total"] == 2
    assert abaixo["janelas"][0]["numero_vendas"] == 1
    assert abaixo["janelas"][0]["quantidade_vendida"] == 1.2
    assert (
        consultar(relatorio, quantidade_operador="acima_de", quantidade_valor="1")[
            "historico_total"
        ]
        == 0
    )


@pytest.mark.parametrize(
    "operador,esperado",
    [
        ("abaixo_de", [-0.5, 0.999, 0.5]),
        ("igual_a", [1]),
        ("acima_de", [-2, 2, 1.001]),
    ],
)
def test_movimentacoes_filtram_magnitude_antes_de_paginar_e_exportar(
    relatorio, operador, esperado
):
    for quantidade in (0.5, 0.999, 1, 1.001, 2, -0.5, -2):
        relatorio.movimento(quantidade)
    relatorio.movimento(0.5, tenant_id=relatorio.outro_tenant)
    parametros = dict(quantidade_operador=operador, quantidade_valor="1", page_size=1)
    pagina = consultar(relatorio, "movimentacoes", **parametros)
    assert pagina["movimentacoes"][0]["saida"] == esperado[0]
    assert pagina["total_registros"] == pagina["pages"] == len(esperado)
    assert pagina["totais"]["total_saidas"] == pytest.approx(sum(esperado))
    exportado = consultar(relatorio, "movimentacoes", export_all=True, **parametros)
    assert [item["saida"] for item in exportado["movimentacoes"]] == esperado
    assert exportado["totais"] == pagina["totais"]
    assert consultar(relatorio, "movimentacoes")["total_registros"] == 7


def test_tipo_datas_e_agrupamento_mensal_combinam_com_quantidade(relatorio):
    relatorio.movimento(2, tipo="entrada")
    relatorio.movimento(3)
    relatorio.movimento(0.5, tipo="entrada")
    relatorio.movimento(2, tipo="entrada", created_at=datetime(2026, 9, 30))
    dados = consultar(
        relatorio,
        "movimentacoes",
        tipo_movimentacao="entrada",
        agrupar_por_mes=True,
        quantidade_operador="acima_de",
        quantidade_valor="1",
    )
    assert dados["total_registros"] == 1
    assert dados["totais"]["total_entradas"] == 2
    assert dados["totais"]["total_saidas"] == 0
    assert dados["meses"][0]["total_entradas"] == 2


@pytest.mark.parametrize("rota", ["produto-vendas", "movimentacoes"])
@pytest.mark.parametrize(
    "parametros",
    [
        {"quantidade_operador": "acima_de"},
        {"quantidade_valor": "1"},
        {"quantidade_operador": "qualquer", "quantidade_valor": "1"},
        {"quantidade_operador": "abaixo_de", "quantidade_valor": "0"},
        {"quantidade_operador": "abaixo_de", "quantidade_valor": "-1"},
        {"quantidade_operador": "abaixo_de", "quantidade_valor": "NaN"},
        {"quantidade_operador": "abaixo_de", "quantidade_valor": "Infinity"},
        {"quantidade_operador": "abaixo_de", "quantidade_valor": "texto"},
    ],
)
def test_api_rejeita_filtro_incompleto_ou_invalido(relatorio, rota, parametros):
    resposta = relatorio.client.get(
        f"/produtos/relatorio/{rota}",
        params={"produto_id": 1, **parametros},
    )
    assert resposta.status_code == 422, resposta.text


def test_filtro_preserva_exigencia_de_permissao(relatorio, monkeypatch):
    def negar(*_args, **_kwargs):
        raise HTTPException(status_code=403, detail="Sem permissão")

    monkeypatch.setattr("app.security.permissions_decorator.check_permission", negar)
    for rota in ("produto-vendas", "movimentacoes"):
        resposta = relatorio.client.get(
            f"/produtos/relatorio/{rota}",
            params={
                "produto_id": 1,
                "quantidade_operador": "acima_de",
                "quantidade_valor": "1",
            },
        )
        assert resposta.status_code == 403
