import importlib.util
from datetime import date
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "zwq20260731a1_comissoes_integridade_fechamento.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "comissoes_integridade_fechamento_migration",
        MIGRATION_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_migration_upgrade_e_downgrade_em_banco_temporario(monkeypatch):
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    sa.Table(
        "tenants",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
    )
    comissoes = sa.Table(
        "comissoes_itens",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("data_pagamento", sa.Date, nullable=True),
        sa.Column("data_atualizacao", sa.DateTime, nullable=True),
        sa.Column("data_venda", sa.Date, nullable=True),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            comissoes.insert(),
            [
                {
                    "id": 1,
                    "status": "paga",
                    "data_pagamento": date(2026, 7, 10),
                    "data_venda": None,
                },
                {
                    "id": 2,
                    "status": "pago_com_compensacao",
                    "data_pagamento": date(2026, 7, 11),
                    "data_venda": None,
                },
                {
                    "id": 3,
                    "status": "pendente",
                    "data_pagamento": None,
                    "data_venda": date(2026, 7, 12),
                },
            ],
        )
        operations = Operations(MigrationContext.configure(connection))
        migration = _load_migration()
        monkeypatch.setattr(migration, "op", operations)

        migration.upgrade()

        inspector = sa.inspect(connection)
        assert "data_fechamento" in {
            column["name"] for column in inspector.get_columns("comissoes_itens")
        }
        assert inspector.has_table("comissoes_configuracoes_sistema")
        statuses = connection.execute(
            sa.text("SELECT status FROM comissoes_itens ORDER BY id")
        ).scalars()
        assert list(statuses) == ["pago", "pago", "pendente"]
        datas_fechamento = connection.execute(
            sa.text("SELECT data_fechamento FROM comissoes_itens ORDER BY id")
        ).scalars()
        assert list(datas_fechamento) == ["2026-07-10", "2026-07-11", None]

        connection.execute(
            sa.text("UPDATE comissoes_itens SET status = 'fechada' WHERE id = 3")
        )
        migration.downgrade()

        inspector = sa.inspect(connection)
        assert "data_fechamento" not in {
            column["name"] for column in inspector.get_columns("comissoes_itens")
        }
        assert not inspector.has_table("comissoes_configuracoes_sistema")
        assert (
            connection.execute(
                sa.text("SELECT status FROM comissoes_itens WHERE id = 3")
            ).scalar_one()
            == "pendente"
        )
