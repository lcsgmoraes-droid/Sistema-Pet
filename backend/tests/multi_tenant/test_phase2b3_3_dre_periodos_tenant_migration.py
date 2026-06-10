import importlib.util
import sys
import types
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import UnsupportedCompilationError
from sqlalchemy.orm import sessionmaker

import app.db  # noqa: F401
from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from app.ia.aba7_models import DREPeriodo
from app.tenancy.context import clear_current_tenant


TENANT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "of20260512a1_add_tenant_id_to_dre_periodos.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_dre_periodos_tenant", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    fake_alembic = types.ModuleType("alembic")
    fake_alembic.op = object()
    original_alembic = sys.modules.get("alembic")
    sys.modules["alembic"] = fake_alembic
    try:
        spec.loader.exec_module(module)
    finally:
        if original_alembic is None:
            sys.modules.pop("alembic", None)
        else:
            sys.modules["alembic"] = original_alembic
    return module


class _FakeOp:
    def __init__(self, connection):
        self.connection = connection

    def get_bind(self):
        return self.connection

    def execute(self, statement):
        if isinstance(statement, str):
            return self.connection.execute(text(statement))
        return self.connection.execute(statement)

    def add_column(self, table_name, column):
        try:
            type_sql = column.type.compile(dialect=self.connection.dialect)
        except UnsupportedCompilationError:
            type_sql = "TEXT"
        nullable_sql = "" if column.nullable else " NOT NULL"
        self.connection.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column.name} {type_sql}{nullable_sql}")
        )

    def drop_column(self, table_name, column_name):
        self.connection.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))


@contextmanager
def _patched_ops(migration, engine):
    with engine.begin() as connection:
        original_op = migration.op
        migration.op = _FakeOp(connection)
        try:
            yield connection
        finally:
            migration.op = original_op


def _tenant_hex(tenant_id):
    return UUID(str(tenant_id)).hex


def _tenant_str(tenant_id):
    return str(UUID(str(tenant_id)))


def _same_tenant(value, tenant_id):
    return str(value).replace("-", "") == _tenant_hex(tenant_id)


def _migration_engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    tenant_id TEXT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE dre_periodos (
                    id INTEGER PRIMARY KEY,
                    usuario_id INTEGER NULL,
                    data_inicio DATE NULL,
                    data_fim DATE NULL,
                    mes INTEGER NULL,
                    ano INTEGER NULL,
                    canal TEXT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO users (id, tenant_id)
                VALUES
                    (1, :tenant_a),
                    (2, NULL)
                """
            ),
            {"tenant_a": _tenant_str(TENANT_A)},
        )
        connection.execute(
            text(
                """
                INSERT INTO dre_periodos
                    (id, usuario_id, data_inicio, data_fim, mes, ano, canal)
                VALUES
                    (10, 1, '2026-05-01', '2026-05-31', 5, 2026, 'loja_fisica'),
                    (11, 2, '2026-06-01', '2026-06-30', 6, 2026, 'loja_fisica'),
                    (12, 999, '2026-07-01', '2026-07-31', 7, 2026, 'loja_fisica')
                """
            )
        )
    return engine


def _index_names(engine):
    return {index["name"] for index in inspect(engine).get_indexes("dre_periodos")}


def test_migration_upgrade_adiciona_tenant_id_nullable_e_backfill():
    migration = _load_migration()
    engine = _migration_engine()

    with _patched_ops(migration, engine):
        migration.upgrade()

    columns = {column["name"]: column for column in inspect(engine).get_columns("dre_periodos")}
    assert "tenant_id" in columns
    assert columns["tenant_id"]["nullable"] is True

    rows = engine.connect().execute(
        text("SELECT id, tenant_id FROM dre_periodos ORDER BY id")
    ).fetchall()
    assert rows[0].tenant_id == _tenant_str(TENANT_A)
    assert rows[1].tenant_id is None
    assert rows[2].tenant_id is None


def test_migration_upgrade_cria_indices_esperados():
    migration = _load_migration()
    engine = _migration_engine()

    with _patched_ops(migration, engine):
        migration.upgrade()

    assert {
        "ix_dre_periodos_tenant_id",
        "ix_dre_periodos_tenant_datas_canal",
        "ix_dre_periodos_tenant_mes_ano_canal",
    }.issubset(_index_names(engine))


def test_migration_downgrade_remove_indices_e_coluna():
    migration = _load_migration()
    engine = _migration_engine()

    with _patched_ops(migration, engine):
        migration.upgrade()
        migration.downgrade()

    columns = {column["name"] for column in inspect(engine).get_columns("dre_periodos")}
    assert "tenant_id" not in columns
    assert not {
        "ix_dre_periodos_tenant_id",
        "ix_dre_periodos_tenant_datas_canal",
        "ix_dre_periodos_tenant_mes_ano_canal",
    }.intersection(_index_names(engine))


def test_dre_periodo_model_tenant_id_not_null():
    # Pós-migração pn20260610a1: tenant_id NOT NULL (mixin TenantScoped).
    assert "tenant_id" in DREPeriodo.__table__.columns
    assert DREPeriodo.__table__.columns["tenant_id"].nullable is False


def _dre_engine():
    clear_current_tenant()
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        for statement in _dre_schema_statements():
            connection.execute(text(statement))
        _seed_dre_sync_data(connection)
    return engine


def _dre_schema_statements():
    return [
        """
        CREATE TABLE dre_categorias (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            nome TEXT,
            ordem INTEGER,
            natureza TEXT,
            ativo BOOLEAN,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE dre_subcategorias (
            id INTEGER NOT NULL,
            tenant_id TEXT NOT NULL,
            categoria_id INTEGER,
            nome TEXT,
            tipo_custo TEXT,
            base_rateio TEXT,
            escopo_rateio TEXT,
            ativo BOOLEAN,
            custo_pe TEXT,
            categoria_financeira_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE dre_periodos (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NULL,
            usuario_id INTEGER,
            data_inicio DATE,
            data_fim DATE,
            mes INTEGER,
            ano INTEGER,
            canal TEXT,
            canais_incluidos TEXT,
            receita_bruta NUMERIC DEFAULT 0,
            deducoes_receita NUMERIC DEFAULT 0,
            receita_liquida NUMERIC DEFAULT 0,
            custo_produtos_vendidos NUMERIC DEFAULT 0,
            lucro_bruto NUMERIC DEFAULT 0,
            margem_bruta_percent NUMERIC DEFAULT 0,
            despesas_vendas NUMERIC DEFAULT 0,
            despesas_administrativas NUMERIC DEFAULT 0,
            despesas_financeiras NUMERIC DEFAULT 0,
            outras_despesas NUMERIC DEFAULT 0,
            total_despesas_operacionais NUMERIC DEFAULT 0,
            lucro_operacional NUMERIC DEFAULT 0,
            margem_operacional_percent NUMERIC DEFAULT 0,
            impostos NUMERIC DEFAULT 0,
            impostos_detalhamento TEXT,
            aliquota_efetiva_percent NUMERIC DEFAULT 0,
            regime_tributario TEXT,
            lucro_liquido NUMERIC DEFAULT 0,
            margem_liquida_percent NUMERIC DEFAULT 0,
            status TEXT,
            tendencia TEXT,
            score_saude INTEGER DEFAULT 0,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE dre_detalhe_canais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            data_inicio DATE,
            data_fim DATE,
            mes INTEGER,
            ano INTEGER,
            canal TEXT,
            receita_bruta NUMERIC DEFAULT 0,
            deducoes_receita NUMERIC DEFAULT 0,
            receita_liquida NUMERIC DEFAULT 0,
            custo_produtos_vendidos NUMERIC DEFAULT 0,
            lucro_bruto NUMERIC DEFAULT 0,
            margem_bruta_percent NUMERIC DEFAULT 0,
            despesas_vendas NUMERIC DEFAULT 0,
            despesas_pessoal NUMERIC DEFAULT 0,
            despesas_administrativas NUMERIC DEFAULT 0,
            despesas_financeiras NUMERIC DEFAULT 0,
            outras_despesas NUMERIC DEFAULT 0,
            total_despesas_operacionais NUMERIC DEFAULT 0,
            lucro_operacional NUMERIC DEFAULT 0,
            margem_operacional_percent NUMERIC DEFAULT 0,
            impostos NUMERIC DEFAULT 0,
            impostos_detalhamento TEXT,
            aliquota_efetiva_percent NUMERIC DEFAULT 0,
            regime_tributario TEXT,
            lucro_liquido NUMERIC DEFAULT 0,
            margem_liquida_percent NUMERIC DEFAULT 0,
            status TEXT,
            score_saude INTEGER DEFAULT 0,
            origem TEXT,
            origem_evento TEXT,
            referencia_id TEXT,
            observacao TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            tenant_id TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE dre_lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            usuario_id INTEGER,
            dre_detalhe_canal_id INTEGER,
            dre_subcategoria_id INTEGER,
            canal TEXT,
            valor NUMERIC,
            data_lancamento DATE,
            data_competencia DATE,
            origem TEXT,
            descricao TEXT
        )
        """,
    ]


def _seed_dre_sync_data(connection):
    for categoria_id, subcategoria_id, tenant_id, nome in (
        (1, 10, TENANT_A, "Despesa Tenant A"),
        (2, 20, TENANT_B, "Despesa Tenant B"),
    ):
        connection.execute(
            text(
                """
                INSERT INTO dre_categorias (
                    id, tenant_id, nome, ordem, natureza, ativo
                ) VALUES (
                    :id, :tenant_id, :nome, 1, 'despesa', 1
                )
                """
            ),
            {"id": categoria_id, "tenant_id": _tenant_hex(tenant_id), "nome": nome},
        )
        connection.execute(
            text(
                """
                INSERT INTO dre_subcategorias (
                    id, tenant_id, categoria_id, nome, tipo_custo, escopo_rateio, ativo
                ) VALUES (
                    :id, :tenant_id, :categoria_id, :nome, 'DIRETO', 'AMBOS', 1
                )
                """
            ),
            {
                "id": subcategoria_id,
                "tenant_id": _tenant_hex(tenant_id),
                "categoria_id": categoria_id,
                "nome": nome,
            },
        )
    connection.execute(
        text(
            """
            INSERT INTO dre_periodos (
                id, tenant_id, usuario_id, data_inicio, data_fim, mes, ano, canal
            ) VALUES
                (1, :tenant_a, 1001, '2026-05-01', '2026-05-31', 5, 2026, 'loja_fisica'),
                (2, :tenant_b, 2002, '2026-05-01', '2026-05-31', 5, 2026, 'loja_fisica')
            """
        ),
        {"tenant_a": _tenant_hex(TENANT_A), "tenant_b": _tenant_hex(TENANT_B)},
    )


def test_atualizar_dre_por_lancamento_usa_periodo_do_tenant_correto():
    engine = _dre_engine()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        atualizar_dre_por_lancamento(
            db=db,
            tenant_id=TENANT_B,
            dre_subcategoria_id=20,
            canal="loja_fisica",
            valor=Decimal("30.00"),
            data_lancamento=date(2026, 5, 12),
            tipo_movimentacao="DESPESA",
        )

        detalhe = db.execute(
            text(
                """
                SELECT tenant_id, usuario_id, lucro_liquido
                FROM dre_detalhe_canais
                """
            )
        ).fetchone()
        assert detalhe is not None
        assert _same_tenant(detalhe.tenant_id, TENANT_B)
        assert detalhe.usuario_id == 2002
        assert float(detalhe.lucro_liquido) == -30.0
    finally:
        db.close()
        clear_current_tenant()
