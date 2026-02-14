from logging.config import fileConfig
import sys
import os
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Adicionar o diretório raiz do backend ao sys.path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
# ### MULTI-TENANT DATABASE URL OVERRIDE ###
# Garante que o Alembic use o MESMO DATABASE_URL do app
from app.config import get_database_url
config.set_main_option('sqlalchemy.url', get_database_url())

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ============================================================================
# METADATA CONFIGURATION (AUTOGENERATE MODE)
# ============================================================================
# ✅ MODO DESENVOLVIMENTO: Habilitar autogenerate
# Importar Base e todos os models para que Alembic detecte as tabelas
# ============================================================================

from app.db.base_class import Base

# Importar todos os models (o db.base já faz isso, mas explícito é melhor)
import app.models  # User, Cliente, etc (arquivo models.py)
import app.fiscal_models  # Models fiscais (diretório fiscal_models/)
import app.produtos_models
import app.vendas_models
import app.caixa_models
import app.financeiro_models
import app.comissoes_models
import app.comissoes_avancadas_models
import app.formas_pagamento_models
import app.idempotency_models
import app.cargo_models
import app.segmentacao_models
import app.rotas_entrega_models
import app.opportunities_models
import app.opportunity_events_models
import app.dre_plano_contas_models

# IA models
from app.ia import aba7_models, aba7_extrato_models

# Configurar metadata para autogenerate
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
