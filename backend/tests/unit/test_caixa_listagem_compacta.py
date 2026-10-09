"""Lista leve e paginada sem consultas ao histórico das movimentações."""

from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session, raiseload
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user_and_tenant
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.caixa_routes import listar_caixas, obter_caixa_aberto, router
from app.db import Base, get_session
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.financeiro_models import ContaReceber
from app import produtos_models  # noqa: F401 - relacionamentos ORM da venda
from app.vendas_models import Venda


@pytest.fixture
def listagem(tenant_context):
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Caixa.__table__,
            MovimentacaoCaixa.__table__,
            Venda.__table__,
            ContaReceber.__table__,
            EmpresaConfigGeral.__table__,
        ],
    )
    tenant, outro = uuid4(), uuid4()
    tenant_context(tenant)
    usuario = SimpleNamespace(id=7, nome="Operador", email="operador@example.test")
    referencia = {"caixa_id": 219, "numero_caixa": 219, "valor_fechamento": 105}
    with Session(engine) as db:
        db.execute(
            EmpresaConfigGeral.__table__.insert().values(
                tenant_id=tenant,
                caixa_compartilhado=False,
            )
        )
        caixas = []
        for id_, tenant_id, usuario_id in [
            *[(id_, tenant, usuario.id) for id_ in range(1, 221)],
            (400, tenant, 8),
            (500, outro, usuario.id),
        ]:
            aberto = id_ in {220, 400, 500}
            caixas.append(
                {
                    "id": id_,
                    "tenant_id": tenant_id,
                    "numero_caixa": id_,
                    "usuario_id": usuario_id,
                    "usuario_nome": f"Operador {usuario_id}",
                    "status": "aberto" if aberto else "fechado",
                    "data_abertura": datetime(2026, 10, 9 if aberto else 8, 9),
                    "data_fechamento": None if aberto else datetime(2026, 10, 8, 20),
                    "valor_abertura": 100,
                    "valor_esperado": None if aberto else 105,
                    "valor_informado": None if aberto else 105,
                    "diferenca": None if aberto else 0,
                    "conferencia_abertura": referencia if id_ == 220 else None,
                }
            )
        db.execute(Caixa.__table__.insert(), caixas)
        db.commit()
        yield SimpleNamespace(
            db=db,
            engine=engine,
            tenant=tenant,
            outro=outro,
            auth=(usuario, tenant),
            referencia=referencia,
        )
    engine.dispose()


def _inserir_historico(caso, quantidade):
    if not quantidade:
        return
    caso.db.execute(
        Venda.__table__.insert(),
        [
            {
                "id": id_,
                "tenant_id": caso.tenant,
                "numero_venda": f"V-{id_}",
                "vendedor_id": 7,
                "user_id": 7,
                "subtotal": 1,
                "total": 1,
                "status": "finalizada",
                "caixa_id": (id_ % 220) + 1,
            }
            for id_ in range(1, quantidade + 1)
        ],
    )
    caso.db.execute(
        MovimentacaoCaixa.__table__.insert(),
        [
            {
                "id": id_,
                "tenant_id": caso.tenant,
                "caixa_id": (id_ % 220) + 1,
                "venda_id": id_,
                "tipo": "venda",
                "forma_pagamento": "Dinheiro",
                "valor": 1,
                "usuario_id": 7,
                "usuario_nome": "Operador",
            }
            for id_ in range(1, quantidade + 1)
        ],
    )
    caso.db.commit()
    caso.db.expire_all()


@contextmanager
def _consultas(engine):
    consultas = []

    def capturar(_conn, _cursor, statement, _parameters, _context, _executemany):
        consultas.append(" ".join(statement.lower().split()))

    event.listen(engine, "before_cursor_execute", capturar)
    try:
        yield consultas
    finally:
        event.remove(engine, "before_cursor_execute", capturar)


def _apenas_config_e_caixas(consultas):
    assert len(consultas) == 2
    assert "from empresa_config_geral" in consultas[0]
    assert "from caixas" in consultas[1]
    assert not any(
        "from movimentacoes_caixa" in sql
        or "from vendas" in sql
        or "join vendas" in sql
        for sql in consultas
    )


@pytest.mark.parametrize("quantidade", [0, 1747])
def test_compacto_tem_duas_consultas_sem_movimentos_ou_vendas(listagem, quantidade):
    caso = listagem
    _inserir_historico(caso, quantidade)
    with _consultas(caso.engine) as consultas:
        caixas = listar_caixas(
            db=caso.db,
            current_user_and_tenant=caso.auth,
            compact=True,
            limit=26,
        )
    _apenas_config_e_caixas(consultas)
    assert [caixa["id"] for caixa in caixas] == [220, *range(219, 194, -1)]
    assert all("movimentacoes" not in caixa for caixa in caixas)
    with _consultas(caso.engine) as consultas:
        aberto = obter_caixa_aberto(caso.db, caso.auth, compact=True)
    _apenas_config_e_caixas(consultas)
    assert aberto["id"] == 220 and "movimentacoes" not in aberto
    assert aberto["conferencia_abertura"] == caso.referencia
    assert aberto["valor_abertura"] == 100


def test_serializacao_compacta_nao_toca_relacao_bloqueada(listagem):
    caso = listagem
    caixa = caso.db.query(Caixa).options(raiseload("*")).filter(Caixa.id == 220).one()
    with _consultas(caso.engine) as consultas:
        dados = caixa.to_dict(incluir_movimentacoes=False)
    assert consultas == []
    assert dados["id"] == 220 and "movimentacoes" not in dados
    with pytest.raises(InvalidRequestError):
        caixa.to_dict()


def test_chamadas_python_antigas_preservam_full_sem_query_como_default(listagem):
    caso = listagem
    _inserir_historico(caso, 1)
    caixas = listar_caixas(None, None, None, caso.db, caso.auth)
    assert len(caixas) == 220
    assert "movimentacoes" in caixas[0]
    caixa_com_movimento = next(caixa for caixa in caixas if caixa["id"] == 2)
    assert caixa_com_movimento["movimentacoes"][0]["venda_numero"] == "V-1"
    assert "movimentacoes" in obter_caixa_aberto(caso.db, caso.auth)


def test_paginacao_estavel_e_filtros_antes_do_limite(listagem):
    caso = listagem
    primeira = listar_caixas(
        db=caso.db, current_user_and_tenant=caso.auth, compact=True, limit=26
    )
    segunda = listar_caixas(
        db=caso.db, current_user_and_tenant=caso.auth, compact=True, limit=26, offset=25
    )
    assert primeira[25]["id"] == segunda[0]["id"]
    assert not set(caixa["id"] for caixa in primeira[:25]).intersection(
        caixa["id"] for caixa in segunda[:25]
    )
    assert [caixa["id"] for caixa in segunda] == list(range(195, 169, -1))
    filtrados = listar_caixas(
        data_inicio="2026-10-09T00:00:00",
        data_fim="2026-10-09T23:59:59",
        status_filter="aberto",
        db=caso.db,
        current_user_and_tenant=caso.auth,
        compact=True,
        limit=26,
    )
    assert [caixa["id"] for caixa in filtrados] == [220]
    assert (
        listar_caixas(
            db=caso.db,
            current_user_and_tenant=caso.auth,
            compact=True,
            limit=26,
            offset=220,
        )
        == []
    )


def test_compartilhado_amplia_usuario_mas_preserva_tenant(listagem):
    caso = listagem
    config = caso.db.query(EmpresaConfigGeral).filter_by(tenant_id=caso.tenant).one()
    config.caixa_compartilhado = True
    caso.db.flush()
    caixas = listar_caixas(db=caso.db, current_user_and_tenant=caso.auth, compact=True)
    assert len(caixas) == 221
    assert 400 in {caixa["id"] for caixa in caixas}
    assert 500 not in {caixa["id"] for caixa in caixas}
    assert all(caixa["compartilhado"] for caixa in caixas)
    assert obter_caixa_aberto(caso.db, caso.auth, compact=True)["id"] == 220
    caso.db.execute(
        Caixa.__table__.update().where(Caixa.id == 220).values(status="fechado")
    )
    caso.db.expire_all()
    assert obter_caixa_aberto(caso.db, caso.auth, compact=True)["id"] == 400
    config = caso.db.query(EmpresaConfigGeral).filter_by(tenant_id=caso.tenant).one()
    config.caixa_compartilhado = False
    caso.db.flush()
    assert obter_caixa_aberto(caso.db, caso.auth, compact=True) is None


@pytest.fixture
def listagem_http(listagem):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_and_tenant] = lambda: listagem.auth
    app.dependency_overrides[get_session] = lambda: listagem.db
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"limit": -1},
        {"offset": -1},
        {"limit": "abc"},
    ],
)
def test_api_valida_limite_e_offset(listagem_http, params):
    assert (
        listagem_http.get("/caixas", params={"compact": True, **params}).status_code
        == 422
    )


def test_api_compacta_preserva_array_objeto_e_full_padrao(listagem_http):
    resposta = listagem_http.get(
        "/caixas", params={"compact": True, "limit": 26, "offset": 25}
    )
    assert resposta.status_code == 200
    assert [caixa["id"] for caixa in resposta.json()] == list(range(195, 169, -1))
    assert all("movimentacoes" not in caixa for caixa in resposta.json())
    assert (
        "movimentacoes"
        not in listagem_http.get("/caixas/aberto", params={"compact": True}).json()
    )
    assert "movimentacoes" in listagem_http.get("/caixas/aberto").json()
