import importlib.util
from pathlib import Path

import sqlalchemy as sa


def test_migration_seeds_one_crediario_per_tenant_and_preserves_existing(monkeypatch):
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "zwz20260824a1_seed_crediario_padrao.py"
    )
    spec = importlib.util.spec_from_file_location(
        "seed_crediario_padrao", migration_path
    )
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                """
                CREATE TABLE formas_pagamento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    nome TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    taxa_percentual NUMERIC,
                    taxa_fixa NUMERIC,
                    prazo_dias INTEGER,
                    prazo_recebimento INTEGER,
                    gera_contas_receber BOOLEAN,
                    split_parcelas BOOLEAN,
                    requer_nsu BOOLEAN,
                    ativo BOOLEAN,
                    permite_parcelamento BOOLEAN,
                    max_parcelas INTEGER,
                    parcelas_maximas INTEGER,
                    icone TEXT,
                    cor TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO users (id, tenant_id) VALUES (1, 'tenant-a'), (2, 'tenant-b')"
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO formas_pagamento (
                    tenant_id, user_id, nome, tipo, ativo
                ) VALUES (
                    'tenant-b', 2, 'Crediário', 'crediario', false
                )
                """
            )
        )

        monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
        migration.upgrade()
        migration.upgrade()

        rows = connection.execute(
            sa.text(
                """
                SELECT tenant_id, nome, ativo, gera_contas_receber, prazo_dias
                FROM formas_pagamento
                WHERE tipo = 'crediario'
                ORDER BY tenant_id
                """
            )
        ).all()

    assert rows == [
        ("tenant-a", "Crediário", 1, 1, 30),
        ("tenant-b", "Crediário", 0, None, None),
    ]
