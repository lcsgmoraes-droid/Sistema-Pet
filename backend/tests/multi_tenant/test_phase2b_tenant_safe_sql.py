import pytest
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.orm import sessionmaker

import app.db  # noqa: F401
import app.dre_plano_contas_models  # noqa: F401
from app.dashboard_routes import _dashboard_fetchone
from app.tenancy.context import clear_current_tenant
from app.utils.tenant_safe_sql import (
    TenantSafeSQLError,
    execute_tenant_safe,
    execute_tenant_safe_all,
)
from app.vendas_routes import _listar_pagamentos_venda_para_comissao


TENANT_1 = "11111111-1111-1111-1111-111111111111"
TENANT_2 = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def raw_sql_session():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    session.execute(text("""
        CREATE TABLE vendas (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            status TEXT
        )
    """))
    session.execute(text("""
        CREATE TABLE venda_pagamentos (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            venda_id INTEGER NOT NULL,
            forma_pagamento TEXT,
            valor NUMERIC,
            data_pagamento TEXT
        )
    """))
    session.execute(text("""
        CREATE TABLE clientes (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            tipo_cadastro TEXT,
            ativo BOOLEAN,
            celular TEXT
        )
    """))
    session.execute(
        text("INSERT INTO vendas (id, tenant_id, status) VALUES (:id, :tenant_id, :status)"),
        [
            {"id": 1, "tenant_id": TENANT_1, "status": "finalizada"},
            {"id": 2, "tenant_id": TENANT_2, "status": "finalizada"},
        ],
    )
    session.execute(
        text("""
            INSERT INTO venda_pagamentos
                (id, tenant_id, venda_id, forma_pagamento, valor, data_pagamento)
            VALUES (:id, :tenant_id, :venda_id, :forma_pagamento, :valor, :data_pagamento)
        """),
        [
            {
                "id": 10,
                "tenant_id": TENANT_1,
                "venda_id": 1,
                "forma_pagamento": "pix",
                "valor": 50,
                "data_pagamento": "2026-05-12",
            },
            {
                "id": 11,
                "tenant_id": TENANT_2,
                "venda_id": 1,
                "forma_pagamento": "pix",
                "valor": 500,
                "data_pagamento": "2026-05-12",
            },
        ],
    )
    session.execute(
        text("""
            INSERT INTO clientes (id, tenant_id, tipo_cadastro, ativo, celular)
            VALUES (:id, :tenant_id, :tipo_cadastro, :ativo, :celular)
        """),
        [
            {
                "id": 20,
                "tenant_id": TENANT_1,
                "tipo_cadastro": "cliente",
                "ativo": True,
                "celular": "",
            },
            {
                "id": 21,
                "tenant_id": TENANT_2,
                "tipo_cadastro": "cliente",
                "ativo": True,
                "celular": "",
            },
        ],
    )
    session.commit()

    try:
        yield session
    finally:
        session.close()
        clear_current_tenant()


def test_tenant_scoped_sql_without_tenant_id_fails(raw_sql_session):
    clear_current_tenant()

    with pytest.raises(TenantSafeSQLError, match="tenant_id ausente"):
        execute_tenant_safe(
            raw_sql_session,
            "SELECT id FROM vendas WHERE {tenant_filter}",
        )


def test_tenant_scoped_sql_without_tenant_filter_marker_fails(raw_sql_session):
    with pytest.raises(TenantSafeSQLError, match="sem marcador"):
        execute_tenant_safe(
            raw_sql_session,
            "SELECT id FROM vendas",
            tenant_id=TENANT_1,
        )


def test_template_item_install_mapping_is_tenant_scoped(raw_sql_session):
    with pytest.raises(TenantSafeSQLError, match="sem marcador"):
        execute_tenant_safe(
            raw_sql_session,
            "SELECT id FROM tenant_template_item_installs",
            tenant_id=TENANT_1,
        )


def test_tenant_filter_marker_injects_tenant_id(raw_sql_session):
    rows = execute_tenant_safe_all(
        raw_sql_session,
        "SELECT id FROM vendas WHERE {tenant_filter} ORDER BY id",
        tenant_id=TENANT_1,
    )

    assert [row.id for row in rows] == [1]


def test_tenant_safe_sql_syncs_rls_tenant_before_execute(raw_sql_session, monkeypatch):
    calls = []

    def fake_sync(db, tenant_id=None):
        calls.append((db, tenant_id))

    monkeypatch.setattr("app.utils.tenant_safe_sql.sync_rls_tenant", fake_sync)

    rows = execute_tenant_safe_all(
        raw_sql_session,
        "SELECT id FROM vendas WHERE {tenant_filter} ORDER BY id",
        tenant_id=TENANT_1,
    )

    assert [row.id for row in rows] == [1]
    assert calls == [(raw_sql_session, TENANT_1)]


def test_text_clause_bindparams_are_preserved(raw_sql_session):
    stmt = text(
        "SELECT id FROM vendas WHERE id IN :ids AND {tenant_filter} ORDER BY id"
    ).bindparams(bindparam("ids", expanding=True))

    rows = execute_tenant_safe_all(
        raw_sql_session,
        stmt,
        {"ids": [1, 2]},
        tenant_id=TENANT_1,
    )

    assert [row.id for row in rows] == [1]


def test_global_sql_allowed_when_explicitly_marked(raw_sql_session):
    result = execute_tenant_safe(
        raw_sql_session,
        "SELECT 1",
        require_tenant=False,
        allow_global=True,
        global_reason="health check sem tabela tenant-scoped",
    )

    assert result.scalar() == 1


def test_tenant_safe_sql_does_not_return_other_tenant_rows(raw_sql_session):
    rows = execute_tenant_safe_all(
        raw_sql_session,
        "SELECT id FROM vendas WHERE {tenant_filter} ORDER BY id",
        tenant_id=TENANT_2,
    )

    assert [row.id for row in rows] == [2]


def test_vendas_raw_sql_helper_does_not_cross_tenants(raw_sql_session):
    rows = _listar_pagamentos_venda_para_comissao(
        raw_sql_session,
        venda_id=1,
        tenant_id=TENANT_1,
    )

    assert [row.id for row in rows] == [10]
    assert [float(row.valor) for row in rows] == [50.0]


def test_vendas_raw_sql_helper_without_tenant_fails(raw_sql_session):
    with pytest.raises(TenantSafeSQLError, match="tenant_id ausente"):
        _listar_pagamentos_venda_para_comissao(
            raw_sql_session,
            venda_id=1,
            tenant_id=None,
        )


def test_dashboard_raw_sql_helper_does_not_cross_tenants(raw_sql_session):
    row = _dashboard_fetchone(
        raw_sql_session,
        """
        SELECT COUNT(*) AS qtd
        FROM clientes
        WHERE {tenant_filter}
          AND tipo_cadastro = 'cliente'
          AND ativo = true
        """,
        TENANT_1,
    )

    assert row.qtd == 1


def test_dashboard_raw_sql_helper_without_tenant_fails(raw_sql_session):
    with pytest.raises(TenantSafeSQLError, match="tenant_id ausente"):
        _dashboard_fetchone(
            raw_sql_session,
            "SELECT COUNT(*) AS qtd FROM clientes WHERE {tenant_filter}",
            None,
        )
