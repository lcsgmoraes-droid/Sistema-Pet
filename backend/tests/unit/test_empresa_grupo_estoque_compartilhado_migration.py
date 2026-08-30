import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "zyu20260830a1_estoque_compartilhado_grupo.py"
)


def _carregar_migration():
    spec = importlib.util.spec_from_file_location(
        "estoque_compartilhado_migration", MIGRATION
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_cria_e_remove_estrutura_em_sqlite(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'estoque-compartilhado.db'}")
    metadata = sa.MetaData()
    sa.Table(
        "tenants",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
    )
    sa.Table(
        "produtos",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
    )
    sa.Table(
        "empresa_grupos",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
    )
    sa.Table(
        "venda_itens",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
    )
    metadata.create_all(engine)

    migration = _carregar_migration()
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        inspector = sa.inspect(connection)
        assert "empresa_grupo_estoques_compartilhados" in inspector.get_table_names()
        colunas = {item["name"] for item in inspector.get_columns("venda_itens")}
        assert {
            "estoque_origem_tenant_id",
            "estoque_compartilhado_id",
            "estoque_origem_nome",
        } <= colunas

        migration.downgrade()
        inspector = sa.inspect(connection)
        assert (
            "empresa_grupo_estoques_compartilhados" not in inspector.get_table_names()
        )
        colunas = {item["name"] for item in inspector.get_columns("venda_itens")}
        assert "estoque_origem_tenant_id" not in colunas
        assert "estoque_compartilhado_id" not in colunas
        assert "estoque_origem_nome" not in colunas

    engine.dispose()


def test_politica_postgres_exige_autorizacao_e_membros_ativos():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "CREATE POLICY produtos_grupo_estoque_select ON produtos" in source
    assert "FOR SELECT USING" in source
    assert "egec.produto_origem_id = produtos.id" in source
    assert "egec.empresa_origem_id::text = produtos.tenant_id::text" in source
    assert "egec.empresa_consumidora_id::text" in source
    assert "current_setting('app.tenant_id', true)" in source
    assert "eg.status = 'ativo'" in source
    assert "egmo.status = 'ativo'" in source
    assert "egmc.status = 'ativo'" in source
    assert "egec.status = 'ativo'" in source
