import importlib.util
import json
import sys
import types
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text


TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
MARKER = "reconciliacao_dre_detalhe_canais_2b3_8"
MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "og20260512a1_create_missing_dre_periodos_provisao.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_missing_dre_periodos", MIGRATION_PATH)
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


@contextmanager
def _patched_ops(migration, engine):
    with engine.begin() as connection:
        original_op = migration.op
        migration.op = _FakeOp(connection)
        try:
            yield connection
        finally:
            migration.op = original_op


def _engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        _create_schema(connection)
        _seed(connection)
    return engine


def _create_schema(connection):
    connection.execute(
        text(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NULL,
                nome TEXT NULL,
                email TEXT NULL,
                documento TEXT NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE dre_periodos (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NULL,
                usuario_id INTEGER NULL,
                data_inicio DATE NULL,
                data_fim DATE NULL,
                mes INTEGER NULL,
                ano INTEGER NULL,
                canal TEXT NULL,
                canais_incluidos TEXT NULL,
                receita_bruta NUMERIC NULL,
                deducoes_receita NUMERIC NULL,
                receita_liquida NUMERIC NULL,
                custo_produtos_vendidos NUMERIC NULL,
                lucro_bruto NUMERIC NULL,
                margem_bruta_percent NUMERIC NULL,
                despesas_vendas NUMERIC NULL,
                despesas_administrativas NUMERIC NULL,
                despesas_financeiras NUMERIC NULL,
                outras_despesas NUMERIC NULL,
                total_despesas_operacionais NUMERIC NULL,
                lucro_operacional NUMERIC NULL,
                margem_operacional_percent NUMERIC NULL,
                impostos NUMERIC NULL,
                lucro_liquido NUMERIC NULL,
                margem_liquida_percent NUMERIC NULL,
                status TEXT NULL,
                criado_em TEXT NULL,
                atualizado_em TEXT NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE dre_detalhe_canais (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                usuario_id INTEGER NULL,
                data_inicio DATE NULL,
                data_fim DATE NULL,
                mes INTEGER NULL,
                ano INTEGER NULL,
                canal TEXT NULL,
                receita_bruta NUMERIC NULL
            )
            """
        )
    )


def _seed(connection):
    connection.execute(
        text(
            """
            INSERT INTO users (id, tenant_id, nome, email, documento)
            VALUES
                (1, :tenant_a, 'SENSITIVE_NAME_A', 'SENSITIVE_EMAIL_A', 'SENSITIVE_DOC_A'),
                (2, :tenant_b, 'SENSITIVE_NAME_B', 'SENSITIVE_EMAIL_B', 'SENSITIVE_DOC_B')
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )
    connection.execute(
        text(
            """
            INSERT INTO dre_periodos (
                id, tenant_id, usuario_id, data_inicio, data_fim, mes, ano, canal, status,
                canais_incluidos, receita_bruta
            )
            VALUES
                (10, :tenant_a, 1, '2026-07-01', '2026-07-31', 7, 2026, 'provisao',
                    'manual', 'manual_sem_marker', 123),
                (11, :tenant_a, 1, '2026-10-01', '2026-10-31', 10, 2026, 'provisao',
                    'reconciliado', 'manual_sem_marker', 456)
            """
        ),
        {"tenant_a": TENANT_A},
    )
    connection.execute(
        text(
            """
            INSERT INTO dre_detalhe_canais (
                id, tenant_id, usuario_id, data_inicio, data_fim, mes, ano, canal, receita_bruta
            )
            VALUES
                (100, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'provisao', 1000),
                (101, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'provisao_consumo', 2000),
                (102, :tenant_a, 1, '2026-06-01', '2026-06-30', 6, 2026, 'ajuste_ferias', 3000),
                (103, :tenant_a, 1, '2026-08-01', '2026-08-31', 8, 2026, 'canal_novo', 4000),
                (104, :tenant_a, 999, '2026-09-01', '2026-09-30', 9, 2026, 'provisao', 5000),
                (105, :tenant_a, 2, '2026-10-01', '2026-10-31', 10, 2026, 'provisao', 6000),
                (106, :tenant_a, 1, '2026-07-01', '2026-07-31', 7, 2026, 'ajuste_13', 7000)
            """
        ),
        {"tenant_a": TENANT_A},
    )


def _marked_rows(connection):
    return connection.execute(
        text(
            """
            SELECT *
            FROM dre_periodos
            WHERE canais_incluidos LIKE :marker
            ORDER BY data_inicio
            """
        ),
        {"marker": f"%{MARKER}%"},
    ).mappings().all()


def test_upgrade_cria_um_periodo_por_grupo_e_mapeia_canais_para_provisao():
    migration = _load_migration()
    engine = _engine()

    with _patched_ops(migration, engine) as connection:
        migration.upgrade()
        rows = _marked_rows(connection)

    assert len(rows) == 2
    assert {row["canal"] for row in rows} == {"provisao"}
    assert {row["mes"] for row in rows} == {5, 6}

    may_payload = json.loads(rows[0]["canais_incluidos"])
    assert may_payload["marcador"] == MARKER
    assert may_payload["canal_canonico"] == "provisao"
    assert may_payload["canais_originais"] == ["provisao", "provisao_consumo"]


def test_upgrade_nao_cria_para_canal_desconhecido_usuario_inexistente_ou_tenant_errado():
    migration = _load_migration()
    engine = _engine()

    with _patched_ops(migration, engine) as connection:
        migration.upgrade()
        rows = connection.execute(
            text(
                """
                SELECT mes, canal, COUNT(*) AS total
                FROM dre_periodos
                GROUP BY mes, canal
                ORDER BY mes
                """
            )
        ).mappings().all()

    by_month = {(row["mes"], row["canal"]): row["total"] for row in rows}
    assert (8, "provisao") not in by_month
    assert (9, "provisao") not in by_month
    assert by_month[(10, "provisao")] == 1


def test_upgrade_e_idempotente_e_nao_cria_duplicado_se_periodo_existe():
    migration = _load_migration()
    engine = _engine()

    with _patched_ops(migration, engine) as connection:
        migration.upgrade()
        migration.upgrade()
        marked_count = len(_marked_rows(connection))
        july_count = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM dre_periodos
                WHERE mes = 7 AND canal = 'provisao'
                """
            )
        ).scalar()

    assert marked_count == 2
    assert july_count == 1


def test_upgrade_nao_altera_detalhes_e_nao_copia_valores_financeiros():
    migration = _load_migration()
    engine = _engine()

    with _patched_ops(migration, engine) as connection:
        detalhes_antes = connection.execute(
            text("SELECT COUNT(*), COALESCE(SUM(receita_bruta), 0) FROM dre_detalhe_canais")
        ).one()
        migration.upgrade()
        detalhes_depois = connection.execute(
            text("SELECT COUNT(*), COALESCE(SUM(receita_bruta), 0) FROM dre_detalhe_canais")
        ).one()
        rows = _marked_rows(connection)

    assert detalhes_depois == detalhes_antes
    assert {float(row["receita_bruta"]) for row in rows} == {0.0}
    assert {float(row["lucro_liquido"]) for row in rows} == {0.0}


def test_downgrade_remove_apenas_periodos_marcados_pela_migration():
    migration = _load_migration()
    engine = _engine()

    with _patched_ops(migration, engine) as connection:
        migration.upgrade()
        migration.downgrade()
        marked_count = len(_marked_rows(connection))
        remaining_manual = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM dre_periodos
                WHERE canal = 'provisao'
                  AND canais_incluidos = 'manual_sem_marker'
                """
            )
        ).scalar()

    assert marked_count == 0
    assert remaining_manual == 2
