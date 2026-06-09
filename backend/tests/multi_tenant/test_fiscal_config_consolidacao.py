"""
Consolidação do domínio fiscal (kit/produto/variacao_config_fiscal).
====================================================================

Estes testes travam o resultado da consolidação:

1. Definição ORM ÚNICA e alinhada ao schema real (migration bda1c213cae2):
   - KitConfigFiscal usa cfop_venda/cfop_compra (NÃO a coluna fantasma `cfop`),
     tem pis_cst/cofins_cst/observacao_fiscal e produto_kit_id NOT NULL.
   - ProdutoConfigFiscal mantém cfop_venda/cfop_compra.
2. Bug de tipo corrigido: VariacaoConfigFiscal.tenant_id é UUID (não Integer).
3. Os três modelos entram no filtro global de tenant via mixin TenantScoped:
   - query SEM tenant no contexto => fail-fast (RuntimeError);
   - query COM tenant no contexto => não quebra (protege o sync do Bling).
"""
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.base_models import TenantScoped
from app.db import Base
from app.kit_config_fiscal_models import KitConfigFiscal
from app.produto_config_fiscal_models import ProdutoConfigFiscal
from app.variacao_config_fiscal_models import VariacaoConfigFiscal

# Resolve a tabela-alvo das ForeignKeys (produtos.id) sem puxar o metadata inteiro
# do app (que esbarra em índices duplicados de outros modelos no create_all).
import app.produtos_models  # noqa: F401


MODELOS_FISCAIS = (KitConfigFiscal, ProdutoConfigFiscal, VariacaoConfigFiscal)


def _colunas(model) -> set[str]:
    return {c.name for c in model.__table__.columns}


@pytest.fixture
def fiscal_session():
    """Sessão SQLite isolada com APENAS as três tabelas fiscais consolidadas.

    Evita o create_all do metadata completo (que falha por um índice duplicado
    pré-existente em opportunity_events) e mantém o teste auto-contido. O filtro
    global de tenant (do_orm_execute) é registrado na classe Session, então atua
    nesta sessão normalmente.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            ProdutoConfigFiscal.__table__,
            KitConfigFiscal.__table__,
            VariacaoConfigFiscal.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# (1) Schema canônico alinhado à migration
# ---------------------------------------------------------------------------

def test_kit_config_fiscal_bate_com_schema_real():
    cols = _colunas(KitConfigFiscal)
    assert {"cfop_venda", "cfop_compra"} <= cols
    assert {"pis_cst", "cofins_cst", "observacao_fiscal"} <= cols
    # coluna fantasma que não existe na tabela real (migration usa cfop_venda/compra)
    assert "cfop" not in cols
    assert KitConfigFiscal.__table__.c.produto_kit_id.nullable is False


def test_produto_config_fiscal_mantem_cfop_venda_compra():
    cols = _colunas(ProdutoConfigFiscal)
    assert {"cfop_venda", "cfop_compra"} <= cols
    assert "cfop" not in cols


# ---------------------------------------------------------------------------
# (2) Bug de tipo: tenant_id UUID
# ---------------------------------------------------------------------------

def test_variacao_tenant_id_e_uuid():
    tenant_col = VariacaoConfigFiscal.__table__.c.tenant_id
    assert isinstance(tenant_col.type, PG_UUID)
    assert tenant_col.nullable is False


# ---------------------------------------------------------------------------
# (3) Adoção do mixin TenantScoped (entra no filtro automático)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model", MODELOS_FISCAIS, ids=lambda m: m.__name__)
def test_modelo_fiscal_e_tenant_scoped(model):
    assert issubclass(model, TenantScoped)


@pytest.mark.parametrize("model", MODELOS_FISCAIS, ids=lambda m: m.__name__)
def test_query_sem_tenant_faz_fail_fast(fiscal_session, model):
    """Sem tenant no contexto, o filtro global deve bloquear (fail-fast)."""
    from app.tenancy.context import clear_current_tenant

    clear_current_tenant()
    with pytest.raises(RuntimeError):
        fiscal_session.query(model).first()


@pytest.mark.parametrize("model", MODELOS_FISCAIS, ids=lambda m: m.__name__)
def test_query_com_tenant_nao_quebra(fiscal_session, tenant_context, model):
    """Com tenant no contexto (como nos fluxos do Bling), a query funciona."""
    tenant_context(uuid4())
    # Não deve levantar; tabela vazia => None.
    assert fiscal_session.query(model).first() is None


# ---------------------------------------------------------------------------
# (4) Migration idempotente: cria a tabela com tenant_id UUID em banco limpo
# ---------------------------------------------------------------------------

def _carregar_migration():
    import importlib.util
    from pathlib import Path

    mig_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "pk20260609a1_create_variacao_config_fiscal.py"
    )
    spec = importlib.util.spec_from_file_location("mig_variacao_cf", mig_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_cria_variacao_config_fiscal_em_banco_limpo():
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    mig = _carregar_migration()
    assert mig.down_revision == "pi20260609a1"

    engine = create_engine("sqlite://", poolclass=StaticPool)
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mig.upgrade()

        insp = inspect(conn)
        assert "variacao_config_fiscal" in insp.get_table_names()
        cols = {c["name"]: c for c in insp.get_columns("variacao_config_fiscal")}
        # tenant_id UUID (compila para CHAR(36) no sqlite via conftest)
        assert "UUID" in str(cols["tenant_id"]["type"]).upper() or "CHAR" in str(
            cols["tenant_id"]["type"]
        ).upper()
        assert {"variacao_id", "cfop_venda", "cfop_compra", "pis_cst", "cofins_cst"} <= set(cols)
        ix = {i["name"] for i in insp.get_indexes("variacao_config_fiscal")}
        assert "ix_variacao_config_fiscal_tenant_id" in ix
    engine.dispose()
