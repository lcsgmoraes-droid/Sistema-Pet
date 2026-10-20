import runpy
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


def test_migration_mensal_preserva_config_programacao_e_historico_de_todas_empresas():
    migration = runpy.run_path(
        str(
            Path(__file__).parents[2]
            / "alembic/versions/zzzzi20261019a1_xml_contabilidade_mensal.py"
        )
    )
    assert migration["down_revision"] == "zzzzh20261019a1"
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE tenants (id TEXT PRIMARY KEY)"))
        conn.execute(
            text(
                "CREATE TABLE xml_contabilidade_config (tenant_id TEXT, envio_automatico BOOLEAN, "
                "envio_automatico_desde TEXT, envio_mensal BOOLEAN, proximo_envio_mensal TEXT)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE xml_contabilidade_envios (tenant_id TEXT, origem TEXT, status TEXT, ultimo_erro TEXT)"
            )
        )
        for tenant in ("empresa-a", "empresa-b"):
            conn.execute(
                text("INSERT INTO tenants VALUES (:tenant)"), {"tenant": tenant}
            )
            conn.execute(
                text(
                    "INSERT INTO xml_contabilidade_config VALUES (:tenant,true,'2026-10-19',true,'2026-11-01')"
                ),
                {"tenant": tenant},
            )
            for origem in ("automatico", "agendado", "manual", "mensal"):
                for status in ("pendente", "agendado", "enviado", "falhou"):
                    conn.execute(
                        text(
                            "INSERT INTO xml_contabilidade_envios VALUES (:tenant,:origem,:status,NULL)"
                        ),
                        {"tenant": tenant, "origem": origem, "status": status},
                    )
        with Operations.context(MigrationContext.configure(conn)):
            migration["upgrade"]()
            migration["downgrade"]()  # rollback não pode reativar envios cancelados.
        configs = (
            conn.execute(text("SELECT * FROM xml_contabilidade_config"))
            .mappings()
            .all()
        )
        assert len(configs) == 2
        for config in configs:
            assert not config["envio_automatico"]
            assert config["envio_automatico_desde"] is None
            assert config["envio_mensal"]
            assert config["proximo_envio_mensal"] == "2026-11-01"
        rows = (
            conn.execute(text("SELECT * FROM xml_contabilidade_envios"))
            .mappings()
            .all()
        )
        assert len(rows) == 32
        assert sum(row["status"] == "cancelado" for row in rows) == 8
        assert sum(row["status"] == "enviado" for row in rows) == 8
        assert sum(row["status"] == "falhou" for row in rows) == 8
        assert all(
            "mensal" in row["ultimo_erro"]
            for row in rows
            if row["status"] == "cancelado"
        )
    engine.dispose()
