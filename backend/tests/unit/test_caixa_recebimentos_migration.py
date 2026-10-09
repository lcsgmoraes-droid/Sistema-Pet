"""Backfill de recebimentos comprovados; históricos ambíguos ficam sem caixa."""

from datetime import datetime
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
import sqlalchemy as sa
from sqlalchemy.schema import CreateSchema, DropSchema


def test_migration_atribui_so_intervalo_unico_e_downgrade_preserva_dados():
    url = os.environ.get("TEST_RECEBIVEIS_POSTGRES_URL")
    if not url:
        pytest.skip("Requer PostgreSQL local para verificar migration e backfill")
    engine = sa.create_engine(url)
    assert engine.url.host in {"localhost", "127.0.0.1"}
    schema = "test_caixa_migration_" + uuid4().hex
    with engine.begin() as conn:
        conn.execute(CreateSchema(schema))
    engine.dispose()
    engine = sa.create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    meta = sa.MetaData()
    tenant, outro_tenant = uuid4(), uuid4()
    caixas = sa.Table(
        "caixas",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("data_abertura", sa.DateTime, nullable=False),
        sa.Column("data_fechamento", sa.DateTime),
    )
    vendas = sa.Table(
        "vendas",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("canal", sa.String),
    )
    pagamentos = sa.Table(
        "venda_pagamentos",
        meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Uuid, nullable=False),
        sa.Column("venda_id", sa.Integer, nullable=False),
        sa.Column("data_pagamento", sa.DateTime),
    )
    arquivo = (
        Path(__file__).parents[2]
        / "alembic/versions/zzzk20261009a1_caixa_recebimentos.py"
    )
    spec = importlib.util.spec_from_file_location(
        "migration_caixa_recebimentos", arquivo
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    try:
        meta.create_all(engine)
        with engine.begin() as conn:
            conn.execute(
                caixas.insert(),
                [
                    {
                        "id": 1,
                        "tenant_id": tenant,
                        "data_abertura": datetime(2026, 10, 1, 8),
                        "data_fechamento": datetime(2026, 10, 1, 20),
                    },
                    {
                        "id": 2,
                        "tenant_id": tenant,
                        "data_abertura": datetime(2026, 10, 2, 8),
                        "data_fechamento": datetime(2026, 10, 2, 20),
                    },
                    {
                        "id": 3,
                        "tenant_id": tenant,
                        "data_abertura": datetime(2026, 10, 3, 8),
                        "data_fechamento": None,
                    },
                    {
                        "id": 4,
                        "tenant_id": tenant,
                        "data_abertura": datetime(2026, 10, 3, 9),
                        "data_fechamento": None,
                    },
                    {
                        "id": 5,
                        "tenant_id": outro_tenant,
                        "data_abertura": datetime(2026, 10, 1, 8),
                        "data_fechamento": None,
                    },
                ],
            )
            conn.execute(
                vendas.insert(),
                [
                    {"id": 1, "tenant_id": tenant, "canal": "loja_fisica"},
                    {"id": 2, "tenant_id": tenant, "canal": "ecommerce"},
                    {"id": 3, "tenant_id": outro_tenant, "canal": "loja_fisica"},
                ],
            )
            conn.execute(
                pagamentos.insert(),
                [
                    {
                        "id": 1,
                        "tenant_id": tenant,
                        "venda_id": 1,
                        "data_pagamento": datetime(2026, 10, 2, 12),
                    },
                    {
                        "id": 2,
                        "tenant_id": tenant,
                        "venda_id": 1,
                        "data_pagamento": datetime(2026, 10, 3, 12),
                    },
                    {
                        "id": 3,
                        "tenant_id": tenant,
                        "venda_id": 2,
                        "data_pagamento": datetime(2026, 10, 2, 12),
                    },
                    {
                        "id": 4,
                        "tenant_id": outro_tenant,
                        "venda_id": 3,
                        "data_pagamento": datetime(2026, 10, 3, 12),
                    },
                    {
                        "id": 5,
                        "tenant_id": outro_tenant,
                        "venda_id": 1,
                        "data_pagamento": datetime(2026, 10, 2, 12),
                    },
                    {
                        "id": 6,
                        "tenant_id": tenant,
                        "venda_id": 1,
                        "data_pagamento": datetime(2026, 10, 1, 7),
                    },
                ],
            )
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()
            resultado = dict(
                conn.execute(
                    sa.text("SELECT id, caixa_id FROM venda_pagamentos ORDER BY id")
                ).all()
            )
            assert resultado == {1: 2, 2: None, 3: None, 4: 5, 5: None, 6: None}
            with Operations.context(MigrationContext.configure(conn)):
                migration.downgrade()
            colunas = {
                c["name"] for c in sa.inspect(conn).get_columns("venda_pagamentos")
            }
            assert "caixa_id" not in colunas
            assert (
                conn.execute(
                    sa.select(sa.func.count()).select_from(pagamentos)
                ).scalar()
                == 6
            )
    finally:
        with engine.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True))
        engine.dispose()
