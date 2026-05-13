import inspect

import app.db  # noqa: F401
from app.base_models import BaseTenantModel
from app.domain.dre import lancamento_dre_sync, rateio_engine
from app.ia.aba7_dre_detalhada_models import DREDetalheCanal
from app.ia.aba7_models import DREPeriodo


def test_dre_periodo_model_ainda_nao_e_tenant_scoped():
    columns = set(DREPeriodo.__table__.columns.keys())

    assert DREPeriodo.__tablename__ == "dre_periodos"
    assert not issubclass(DREPeriodo, BaseTenantModel)
    assert "tenant_id" in columns
    assert DREPeriodo.__table__.columns["tenant_id"].nullable is True
    assert "usuario_id" in columns
    assert "status" in columns
    assert "fechado" not in columns


def test_lancamento_dre_sync_periodo_query_filtra_tenant_id_nullable():
    source = inspect.getsource(lancamento_dre_sync.atualizar_dre_por_lancamento)

    assert "db.query(DREPeriodo)" in source
    assert "DREPeriodo.tenant_id == tenant_id" in source
    assert "DREPeriodo.data_inicio <= data_lancamento" in source
    assert "DREPeriodo.data_fim >= data_lancamento" in source
    assert "DREPeriodo.usuario_id" not in source


def test_rateio_engine_referencia_campos_ausentes_no_model_atual():
    source = inspect.getsource(rateio_engine.calcular_rateio_dre)

    assert "periodo.fechado" in source
    assert not hasattr(DREPeriodo, "fechado")

    assert "DREDetalheCanal.periodo_id" in source
    assert not hasattr(DREDetalheCanal, "periodo_id")

    assert "canal.faturamento" in source
    assert not hasattr(DREDetalheCanal, "faturamento")

    assert "canal.total_pedidos" in source
    assert not hasattr(DREDetalheCanal, "total_pedidos")

    assert "canal.aplicar_rateio" in source
    assert not hasattr(DREDetalheCanal, "aplicar_rateio")


def test_rateio_engine_ainda_nao_tem_fail_fast_de_tenant():
    source = inspect.getsource(rateio_engine.calcular_rateio_dre)

    assert "tenant_id" in source
    assert "TenantSafeSQLError" not in source
    assert "get_current_tenant_id" not in source
    assert "set_tenant_context" not in source


def test_migration_base_de_dre_periodos_nao_criou_tenant_id():
    with open(
        "backend/alembic/versions/bda1c213cae2_base_inicial_completa.py",
        encoding="utf-8",
    ) as migration_file:
        migration_source = migration_file.read()

    create_start = migration_source.index("op.create_table('dre_periodos'")
    create_end = migration_source.index(
        "op.create_index(op.f('ix_dre_periodos_id')",
        create_start,
    )
    dre_periodos_ddl = migration_source[create_start:create_end]

    assert "sa.Column('usuario_id'" in dre_periodos_ddl
    assert "tenant_id" not in dre_periodos_ddl
