"""Snapshots reais: FORCE RLS, vínculo à empresa e histórico imutável em PG."""

import json
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

TABELA = "xml_contabilidade_tentativas"


def _migration(nome):
    return runpy.run_path(str(Path(__file__).parents[2] / "alembic/versions" / nome))


def _registrar(conn, tenant, envio_id, numero=1):
    snapshot = {"contagens": {"notas_enviadas": 2, "notas_pendentes": 1}}
    return conn.execute(
        text(
            f"INSERT INTO {TABELA} "
            "(tenant_id,envio_id,numero_tentativa,iniciado_em,concluido_em,"
            "resultado,resumo,snapshot) VALUES "
            "(:tenant,:envio,:numero,now(),now(),'enviado_com_pendencias',"
            "CAST(:dados AS json),CAST(:dados AS json)) RETURNING id"
        ),
        {
            "tenant": tenant,
            "envio": envio_id,
            "numero": numero,
            "dados": json.dumps(snapshot),
        },
    ).scalar_one()


def test_relatorio_pg_isola_empresas_restringe_vinculo_e_preserva_tentativas():
    url = os.environ.get("XML_CONTABILIDADE_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Defina XML_CONTABILIDADE_TEST_POSTGRES_URL para PostgreSQL local")
    parsed = make_url(url)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert parsed.database == "postgres"
    schema, role = f"xml_rel_{uuid4().hex}", f"xml_rel_role_{uuid4().hex}"
    tenant_a, tenant_b = str(uuid4()), str(uuid4())
    base = _migration("zzzzh20261019a1_xml_contabilidade.py")
    nova = _migration("zzzzk20261020a1_xml_contabilidade_tentativas.py")
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                conn.exec_driver_sql(f"CREATE SCHEMA {schema}")
                conn.exec_driver_sql(f"SET LOCAL search_path TO {schema}")
                with Operations.context(MigrationContext.configure(conn)):
                    base["upgrade"]()
                    nova["upgrade"]()
                envios = {}
                for tenant in (tenant_a, tenant_b):
                    envios[tenant] = conn.execute(
                        text(
                            "INSERT INTO xml_contabilidade_envios "
                            "(tenant_id,origem,status,email_destino,data_inicio,"
                            "data_fim,proxima_tentativa_em) VALUES "
                            "(:tenant,'manual','enviado','contador@example.test',"
                            "'2026-10-01','2026-10-19',now()) RETURNING id"
                        ),
                        {"tenant": tenant},
                    ).scalar_one()
                    _registrar(conn, tenant, envios[tenant])
                conn.exec_driver_sql(f"CREATE ROLE {role} NOSUPERUSER NOBYPASSRLS")
                conn.exec_driver_sql(f"GRANT USAGE,CREATE ON SCHEMA {schema} TO {role}")
                conn.exec_driver_sql(f"ALTER TABLE {TABELA} OWNER TO {role}")
                conn.exec_driver_sql(f"SET LOCAL ROLE {role}")
                assert conn.execute(
                    text(
                        "SELECT NOT rolsuper AND NOT rolbypassrls FROM pg_roles "
                        "WHERE rolname=current_user"
                    )
                ).scalar_one()
                assert conn.execute(
                    text(
                        "SELECT relrowsecurity AND relforcerowsecurity "
                        "FROM pg_class WHERE oid=CAST(:tabela AS regclass)"
                    ),
                    {"tabela": TABELA},
                ).scalar_one()
                for tenant in (tenant_a, tenant_b, ""):
                    conn.execute(
                        text("SELECT set_config('app.tenant_id', :tenant, true)"),
                        {"tenant": tenant},
                    )
                    rows = conn.execute(
                        text(f"SELECT tenant_id,snapshot FROM {TABELA}")
                    ).all()
                    assert [str(row.tenant_id) for row in rows] == (
                        [tenant] if tenant else []
                    )
                    if rows:
                        assert rows[0].snapshot["contagens"]["notas_pendentes"] == 1
                    foreign = tenant_b if tenant == tenant_a else tenant_a
                    # A empresa atual não enxerga, modifica nem apaga outra empresa.
                    assert (
                        conn.execute(
                            text(
                                f"UPDATE {TABELA} SET resultado='intruso' WHERE tenant_id=:tenant"
                            ),
                            {"tenant": foreign},
                        ).rowcount
                        == 0
                    )
                    assert (
                        conn.execute(
                            text(f"DELETE FROM {TABELA} WHERE tenant_id=:tenant"),
                            {"tenant": foreign},
                        ).rowcount
                        == 0
                    )
                    with pytest.raises(DBAPIError), conn.begin_nested():
                        _registrar(conn, foreign, envios[foreign], 2)
                    if tenant:
                        # Mesmo o dono da tabela não altera um retrato já finalizado.
                        with pytest.raises(DBAPIError), conn.begin_nested():
                            conn.execute(text(f"UPDATE {TABELA} SET snapshot='{{}}'"))
                        with pytest.raises(DBAPIError), conn.begin_nested():
                            conn.execute(text(f"DELETE FROM {TABELA}"))
                        with pytest.raises(DBAPIError), conn.begin_nested():
                            _registrar(conn, tenant, envios[tenant], 1)
                        # Tenant correto não permite vincular o relatório ao envio alheio.
                        with pytest.raises(DBAPIError), conn.begin_nested():
                            _registrar(conn, tenant, envios[foreign], 2)
                        _registrar(conn, tenant, envios[tenant], 2)
                        assert conn.execute(
                            text(
                                f"SELECT numero_tentativa FROM {TABELA} ORDER BY numero_tentativa"
                            )
                        ).scalars().all() == [1, 2]
                conn.exec_driver_sql("RESET ROLE")
                with Operations.context(MigrationContext.configure(conn)):
                    nova["downgrade"]()
                assert not inspect(conn).has_table(TABELA)
                assert inspect(conn).has_table("xml_contabilidade_envios")
                assert not any(
                    index["name"] == "uq_xml_contabilidade_envios_tenant_id_id"
                    for index in inspect(conn).get_indexes("xml_contabilidade_envios")
                )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
