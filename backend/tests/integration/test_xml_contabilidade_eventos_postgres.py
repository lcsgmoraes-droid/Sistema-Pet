"""RLS real dos eventos fiscais em schema temporário, desfeito por rollback."""

import os
import runpy
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

MONITOR = "xml_contabilidade_documentos_monitor"
EVENTOS = "xml_contabilidade_eventos_recebidos"
XML_ORIGINAL = (
    b'<?xml version="1.0" encoding="UTF-8"?>\r\n<evento>corre\xc3\xa7\xc3\xa3o</evento>'
)


def _inserir(conn, tabela, tenant):
    params = {"tenant": tenant, "xml": XML_ORIGINAL}
    if tabela == MONITOR:
        conn.execute(
            text(
                f"INSERT INTO {tabela} (tenant_id,provider,documento_id,proxima_consulta_em) "
                "VALUES (:tenant,'intnfe','nota-1',now())"
            ),
            params,
        )
    else:
        conn.execute(
            text(
                f"INSERT INTO {tabela} (tenant_id,provider,documento_id,chave,identidade,"
                "tipo,sequencia,protocolo,registrado_em,nome_arquivo,xml) VALUES "
                "(:tenant,'intnfe','nota-1',:chave,:identidade,'110110',1,"
                "'123456789012345',now(),'carta-correcao-1.xml',:xml)"
            ),
            {**params, "chave": "1" * 44, "identidade": "110110" + "1" * 44 + "01"},
        )


def test_migration_eventos_postgres_forca_rls_ate_para_dono_e_preserva_xml_original():
    url = os.environ.get("XML_CONTABILIDADE_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Defina XML_CONTABILIDADE_TEST_POSTGRES_URL para PostgreSQL local")
    parsed = make_url(url)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert parsed.database == "postgres"
    schema, role = f"xml_evt_{uuid4().hex}", f"xml_evt_role_{uuid4().hex}"
    tenant_a, tenant_b = str(uuid4()), str(uuid4())
    migration = runpy.run_path(
        str(
            Path(__file__).parents[2]
            / "alembic/versions/zzzzj20261019a1_xml_contabilidade_eventos.py"
        )
    )
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                conn.exec_driver_sql(f"CREATE SCHEMA {schema}")
                conn.exec_driver_sql(f"SET LOCAL search_path TO {schema}")
                with Operations.context(MigrationContext.configure(conn)):
                    migration["upgrade"]()
                conn.exec_driver_sql(f"CREATE ROLE {role} NOSUPERUSER NOBYPASSRLS")
                conn.exec_driver_sql(f"GRANT USAGE,CREATE ON SCHEMA {schema} TO {role}")
                for tabela in (MONITOR, EVENTOS):
                    # A mesma identidade fiscal pode existir em empresas distintas.
                    _inserir(conn, tabela, tenant_a)
                    _inserir(conn, tabela, tenant_b)
                    conn.exec_driver_sql(f"ALTER TABLE {tabela} OWNER TO {role}")
                conn.exec_driver_sql(f"SET LOCAL ROLE {role}")
                assert (
                    conn.execute(
                        text(
                            "SELECT rolbypassrls OR rolsuper FROM pg_roles WHERE rolname=current_user"
                        )
                    ).scalar()
                    is False
                )
                assert (
                    conn.execute(
                        text(
                            "SELECT count(*) FROM pg_class WHERE relnamespace = "
                            "current_schema()::regnamespace AND relname IN (:monitor,:eventos) "
                            "AND relrowsecurity AND relforcerowsecurity "
                            "AND relowner = (SELECT oid FROM pg_roles WHERE rolname=current_user)"
                        ),
                        {"monitor": MONITOR, "eventos": EVENTOS},
                    ).scalar()
                    == 2
                )
                for tenant in (tenant_a, tenant_b, ""):
                    conn.execute(
                        text("SELECT set_config('app.tenant_id', :tenant, true)"),
                        {"tenant": tenant},
                    )
                    foreign = tenant_b if tenant == tenant_a else tenant_a
                    for tabela in (MONITOR, EVENTOS):
                        rows = (
                            conn.execute(text(f"SELECT tenant_id FROM {tabela}"))
                            .scalars()
                            .all()
                        )
                        assert [str(row) for row in rows] == (
                            [tenant] if tenant else []
                        )
                        assert (
                            conn.execute(
                                text(f"DELETE FROM {tabela} WHERE tenant_id=:foreign"),
                                {"foreign": foreign},
                            ).rowcount
                            == 0
                        )
                        assert (
                            conn.execute(
                                text(
                                    f"UPDATE {tabela} SET documento_id='intruso' WHERE tenant_id=:foreign"
                                ),
                                {"foreign": foreign},
                            ).rowcount
                            == 0
                        )
                        with pytest.raises(DBAPIError), conn.begin_nested():
                            _inserir(conn, tabela, str(uuid4()))
                        if tenant:
                            with pytest.raises(DBAPIError), conn.begin_nested():
                                conn.execute(
                                    text(
                                        f"UPDATE {tabela} SET tenant_id=:foreign WHERE tenant_id=:tenant"
                                    ),
                                    {"tenant": tenant, "foreign": foreign},
                                )
                            with pytest.raises(IntegrityError), conn.begin_nested():
                                _inserir(conn, tabela, tenant)
                    if tenant:
                        armazenado = conn.execute(
                            text(f"SELECT xml FROM {EVENTOS}")
                        ).scalar_one()
                        assert bytes(armazenado) == XML_ORIGINAL
                conn.exec_driver_sql("RESET ROLE")
                with Operations.context(MigrationContext.configure(conn)):
                    migration["downgrade"]()
                assert not any(
                    inspect(conn).has_table(tabela) for tabela in (MONITOR, EVENTOS)
                )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
