"""Verifica RLS real sem tocar tabelas existentes; tudo termina em rollback."""

import os
import runpy
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError


def test_migration_postgres_isola_configuracoes_e_envios():
    url = os.environ.get("XML_CONTABILIDADE_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Defina XML_CONTABILIDADE_TEST_POSTGRES_URL para PostgreSQL local")
    parsed = make_url(url)
    assert parsed.host in {"127.0.0.1", "localhost"}
    # A base de manutenção local recebe somente schema e papel temporários.
    assert parsed.database == "postgres"
    schema, role = f"xml_test_{uuid4().hex}", f"xml_role_{uuid4().hex}"
    tenant_a, tenant_b = str(uuid4()), str(uuid4())
    migration = runpy.run_path(
        str(
            Path(__file__).parents[2]
            / "alembic/versions/zzzzh20261019a1_xml_contabilidade.py"
        )
    )
    engine = create_engine(url)
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            conn.exec_driver_sql(f"CREATE SCHEMA {schema}")
            conn.exec_driver_sql(f"SET LOCAL search_path TO {schema}")
            with Operations.context(MigrationContext.configure(conn)):
                migration["upgrade"]()
            conn.exec_driver_sql(f"CREATE ROLE {role} NOSUPERUSER NOBYPASSRLS")
            conn.exec_driver_sql(f"GRANT USAGE ON SCHEMA {schema} TO {role}")
            conn.exec_driver_sql(
                f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {schema} TO {role}"
            )
            conn.exec_driver_sql(
                f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA {schema} TO {role}"
            )
            for tenant in (tenant_a, tenant_b):
                conn.execute(
                    text(
                        "INSERT INTO xml_contabilidade_config (tenant_id,email_contador) VALUES (:tenant,'contador@example.com')"
                    ),
                    {"tenant": tenant},
                )
                conn.execute(
                    text(
                        "INSERT INTO xml_contabilidade_envios (tenant_id,origem,status,email_destino,data_inicio,data_fim,proxima_tentativa_em) VALUES (:tenant,'manual','pendente','contador@example.com','2026-10-01','2026-10-19',now())"
                    ),
                    {"tenant": tenant},
                )
            conn.exec_driver_sql(f"SET LOCAL ROLE {role}")
            for tenant in (tenant_a, tenant_b, ""):
                conn.execute(
                    text("SELECT set_config('app.tenant_id', :tenant, true)"),
                    {"tenant": tenant},
                )
                for tabela in migration["TABLES"]:
                    rows = (
                        conn.execute(text(f"SELECT tenant_id FROM {tabela}"))
                        .scalars()
                        .all()
                    )
                    assert [str(row) for row in rows] == ([tenant] if tenant else [])
                    foreign = tenant_b if tenant == tenant_a else tenant_a
                    assert (
                        conn.execute(
                            text(f"DELETE FROM {tabela} WHERE tenant_id=:tenant"),
                            {"tenant": foreign},
                        ).rowcount
                        == 0
                    )
                    assert (
                        conn.execute(
                            text(
                                f"UPDATE {tabela} SET tenant_id=:foreign WHERE tenant_id=:foreign"
                            ),
                            {"foreign": foreign},
                        ).rowcount
                        == 0
                    )
            conn.execute(
                text("SELECT set_config('app.tenant_id', :tenant, true)"),
                {"tenant": tenant_a},
            )
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(
                    text(
                        "INSERT INTO xml_contabilidade_config (tenant_id) VALUES (:tenant)"
                    ),
                    {"tenant": str(uuid4())},
                )
            conn.exec_driver_sql("RESET ROLE")
            with Operations.context(MigrationContext.configure(conn)):
                migration["downgrade"]()
            assert not inspect(conn).has_table("xml_contabilidade_config")
            assert not inspect(conn).has_table("xml_contabilidade_envios")
        finally:
            transaction.rollback()
    engine.dispose()
