from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base

from app.clientes.schemas import ClienteCreate, ClienteUpdate
from app.routes.app_mobile_funcionario_pdv.schemas import (
    FuncionarioPdvClienteRapidoRequest,
)
from app.routes import ecommerce_auth_cliente as online
from app.routes import app_mobile_routes  # noqa: F401 - registra os modelos relacionados
from app.tenancy.context import tenant_context
from app.services.cliente_origem import (
    filtrar_origem_periodo,
    normalizar_origem_cliente,
    opcoes_origem_cliente,
    resumir_origens,
)


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("Loja Física", "loja_fisica"),
        ("balcão", "loja_fisica"),
        ("site", "ecommerce"),
        ("E-commerce", "ecommerce"),
        ("iFood", "ifood"),
        (" APP ", "app"),
        ("Feira de Adoção", "feira_de_adocao"),
        (None, None),
        ("Não identificada", None),
    ],
)
def test_normaliza_origens_sem_fragmentar_relatorio(entrada, esperado):
    assert normalizar_origem_cliente(entrada) == esperado


def test_cadastro_manual_default_e_update_parcial_preservam_origem():
    assert ClienteCreate(nome="Teste").origem_cliente == "loja_fisica"
    assert FuncionarioPdvClienteRapidoRequest().origem_cliente == "loja_fisica"
    assert (
        ClienteCreate(nome="Teste", origem_cliente="site").origem_cliente == "ecommerce"
    )
    assert ClienteUpdate(origem_cliente="iFood").model_dump(exclude_unset=True) == {
        "origem_cliente": "ifood"
    }
    assert "origem_cliente" not in ClienteUpdate(nome="Novo nome").model_dump(
        exclude_unset=True
    )
    assert ClienteUpdate(origem_cliente=None).model_dump(exclude_unset=True) == {
        "origem_cliente": None
    }


@pytest.mark.parametrize("entrada", ["", "  ", "!!!", "x" * 51, ["app"], 42])
def test_rejeita_origem_invalida(entrada):
    with pytest.raises(ValidationError):
        ClienteCreate(nome="Teste", origem_cliente=entrada)


@pytest.mark.parametrize("canal", ["app", "ecommerce"])
@pytest.mark.parametrize("origem_existente", ["loja_fisica", "ifood", None])
def test_criar_acesso_online_nao_troca_origem_de_cliente_existente(
    monkeypatch, canal, origem_existente
):
    tenant = uuid4()
    user = SimpleNamespace(
        id=2,
        tenant_id=tenant,
        cpf_cnpj=None,
        email="cliente@example.com",
        telefone=None,
        nome="Cliente",
    )
    cliente = SimpleNamespace(
        id=1,
        nome="Cliente",
        email=user.email,
        telefone=None,
        cpf=None,
        ativo=True,
        origem_cliente=origem_existente,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    monkeypatch.setattr(online, "_activate_user_tenant_context", lambda *_: tenant)
    monkeypatch.setattr(
        online, "_find_operational_cliente_match", lambda *a, **kw: None
    )
    monkeypatch.setattr(online, "_find_cliente_match", lambda *a, **kw: cliente)
    assert (
        online._get_or_create_cliente_for_user(db, user, origem_cliente=canal)
        is cliente
    )
    assert cliente.origem_cliente == origem_existente
    assert cliente.auth_user_id == user.id
    db.add.assert_not_called()


@pytest.mark.parametrize("canal", ["app", "ecommerce", None])
def test_novo_cliente_online_recebe_origem_so_quando_conhecida(monkeypatch, canal):
    tenant = uuid4()
    user = SimpleNamespace(
        id=2,
        tenant_id=tenant,
        cpf_cnpj=None,
        email="novo@example.com",
        telefone="11999999999",
        nome="Novo Cliente",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    monkeypatch.setattr(online, "_activate_user_tenant_context", lambda *_: tenant)
    monkeypatch.setattr(
        online, "_find_operational_cliente_match", lambda *a, **kw: None
    )
    monkeypatch.setattr(online, "_find_cliente_match", lambda *a, **kw: None)
    monkeypatch.setattr(online, "gerar_codigo_cliente", lambda *a: "123")
    cliente = online._get_or_create_cliente_for_user(db, user, origem_cliente=canal)
    assert cliente.origem_cliente == canal
    assert cliente.tenant_id == tenant
    db.add.assert_called_once_with(cliente)


@pytest.fixture
def origem_db():
    base = declarative_base()

    class Cliente(base):
        __tablename__ = "clientes_origem_test"
        id = Column(Integer, primary_key=True)
        tenant_id = Column(String)
        origem_cliente = Column(String)
        created_at = Column(DateTime)

    engine = create_engine("sqlite://")
    base.metadata.create_all(engine)
    with tenant_context(uuid4()), Session(engine) as db:
        for tenant, origem, instante in [
            ("loja-a", "app", "2026-09-09T02:59:59"),
            ("loja-a", "app", "2026-09-09T03:00:00"),
            ("loja-a", "ifood", "2026-09-10T02:59:59"),
            ("loja-a", None, "2026-09-09T14:00:00"),
            ("loja-a", "feira", "2026-09-10T03:00:00"),
            ("loja-b", "origem_privada", "2026-09-09T14:00:00"),
        ]:
            db.add(
                Cliente(
                    tenant_id=tenant,
                    origem_cliente=origem,
                    created_at=datetime.fromisoformat(instante),
                )
            )
        db.commit()
        yield db, Cliente
    engine.dispose()


def test_relatorio_considera_dia_local_todas_paginas_e_preserva_filtro_tenant(
    origem_db,
):
    db, model = origem_db
    query = db.query(model).filter(model.tenant_id == "loja-a")
    query = filtrar_origem_periodo(
        query, model, inicio=date(2026, 9, 9), fim=date(2026, 9, 9)
    )
    assert len(query.limit(1).all()) == 1
    resumo = resumir_origens(query, model)
    assert {row["origem"]: row["total"] for row in resumo} == {
        "app": 1,
        "ifood": 1,
        None: 1,
    }
    assert filtrar_origem_periodo(query, model, origem="Não identificada").count() == 1
    assert filtrar_origem_periodo(query, model, origem="iFood").count() == 1
    assert filtrar_origem_periodo(query, model, origem="feira").count() == 0


def test_opcoes_personalizadas_respeitam_tenant(origem_db):
    db, model = origem_db
    opcoes = opcoes_origem_cliente(db, model, ["loja-a"])
    assert {"value": "feira", "label": "Feira"} in opcoes
    assert all(opcao["value"] != "origem_privada" for opcao in opcoes)


def test_periodo_invertido_rejeitado(origem_db):
    db, model = origem_db
    with pytest.raises(ValueError, match="data inicial"):
        filtrar_origem_periodo(
            db.query(model), model, inicio=date(2026, 9, 10), fim=date(2026, 9, 9)
        )


def test_correcao_manual_grava_valor_anterior_e_novo_antes_do_commit(monkeypatch):
    from app.clientes import crud_routes as crud
    from app.models import Cliente

    tenant = uuid4()
    user = SimpleNamespace(id=20)
    cliente = Cliente(
        id=1,
        tenant_id=tenant,
        codigo="1",
        nome="Cliente",
        telefone="11999999999",
        tipo_cadastro="cliente",
        ativo=True,
        origem_cliente="app",
    )
    db = MagicMock()
    audit = MagicMock()
    monkeypatch.setattr(
        crud, "_validar_tenant_e_obter_usuario", lambda _: (user, tenant)
    )
    monkeypatch.setattr(crud, "_obter_cliente_ou_404", lambda *a: cliente)
    monkeypatch.setattr(crud, "_anexar_metadados_criacao_cliente", lambda *a: None)
    monkeypatch.setattr(crud, "log_action", audit)
    monkeypatch.setattr(crud, "log_update", lambda *a: None)

    def commit():
        assert audit.call_args.kwargs["commit"] is False
        assert cliente.origem_cliente == "ifood"

    db.commit.side_effect = commit
    result = crud.update_cliente(
        1, ClienteUpdate(origem_cliente="iFood"), db=db, user_and_tenant=None
    )
    assert result["origem_cliente"] == "ifood"
    assert audit.call_args.kwargs["old_value"] == {"origem_cliente": "app"}
    assert audit.call_args.kwargs["new_value"] == {"origem_cliente": "ifood"}
    assert audit.call_args.kwargs["tenant_id"] == tenant
    db.commit.assert_called_once()


def test_migration_preserva_clientes_antigos_sem_inventar_origem():
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect, text

    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/zzl20260909a1_cliente_origem.py"
    )
    spec = importlib.util.spec_from_file_location("origem_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE clientes (id INTEGER PRIMARY KEY, tenant_id TEXT, created_at TIMESTAMP)"
            )
        )
        conn.execute(text("INSERT INTO clientes VALUES (1, 'loja-a', '2026-09-01')"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
            assert (
                conn.execute(
                    text("SELECT origem_cliente FROM clientes WHERE id=1")
                ).scalar()
                is None
            )
            assert inspect(conn).get_indexes("clientes")[0]["column_names"] == [
                "tenant_id",
                "origem_cliente",
                "created_at",
            ]
            migration.downgrade()
        assert conn.execute(text("SELECT count(*) FROM clientes")).scalar() == 1
        assert "origem_cliente" not in {
            column["name"] for column in inspect(conn).get_columns("clientes")
        }
    engine.dispose()
