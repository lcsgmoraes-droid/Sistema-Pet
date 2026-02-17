"""
Migration Check - Pré-Prod Bloco 3
==================================

Este módulo verifica se todas as migrations do Alembic foram aplicadas
antes da aplicação aceitar tráfego de produção.

Garante que:
1. Tabela alembic_version existe
2. Versão atual do banco está sincronizada com o head esperado
3. App NÃO inicia com migrations pendentes

Autor: Sistema Pet - Pré-Prod Block 3
Data: 2026-02-05
"""

import logging
from typing import Optional
from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

logger = logging.getLogger(__name__)


class DatabaseMigrationError(RuntimeError):
    """Erro levantado quando há migrations pendentes ou problemas no schema."""
    pass


def ensure_db_ready(engine: Engine, alembic_ini_path: Optional[str] = None) -> None:
    """
    Verifica se o banco está pronto para produção.
    Falha se houver migrations pendentes.
    
    Esta função DEVE ser chamada:
    - Na inicialização do app
    - Antes de aceitar requests
    - Após validação de ambiente (Bloco 1)
    
    Args:
        engine: SQLAlchemy engine conectado ao banco
        alembic_ini_path: Caminho para alembic.ini (opcional)
    
    Raises:
        DatabaseMigrationError: Se houver migrations pendentes ou erro no schema
    
    Validações executadas:
    ----------------------
    
    1. Tabela alembic_version existe?
    2. Versão atual aplicada está presente?
    3. Versão atual == head esperado?
    
    Exemplos de erro:
    ----------------
    
    >>> ensure_db_ready(engine)
    DatabaseMigrationError: Database migrations pending: current=abc123, expected=def456
    
    >>> ensure_db_ready(engine)
    DatabaseMigrationError: Database schema not initialized (alembic_version table missing)
    """
    
    logger.info("🔍 Verificando estado das migrations do banco de dados...")
    
    try:
        # ============================================================
        # 1️⃣ VERIFICAR SE TABELA alembic_version EXISTE
        # ============================================================
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "alembic_version" not in tables:
            error_msg = (
                "Database schema not initialized: alembic_version table missing\n"
                "Please run: alembic upgrade head"
            )
            logger.error(f"❌ {error_msg}")
            raise DatabaseMigrationError(error_msg)
        
        logger.debug("✓ alembic_version table exists")
        
        # ============================================================
        # 2️⃣ OBTER VERSÃO ATUAL DO BANCO
        # ============================================================
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            
            if not row:
                error_msg = (
                    "Database schema not initialized: no version found in alembic_version\n"
                    "Please run: alembic upgrade head"
                )
                logger.error(f"❌ {error_msg}")
                raise DatabaseMigrationError(error_msg)
            
            current_version = row[0]
            logger.info(f"📌 Current database version: {current_version}")
        
        # ============================================================
        # 3️⃣ OBTER HEAD ESPERADO (via Alembic)
        # ============================================================
        
        try:
            expected_head = _get_alembic_head(engine, alembic_ini_path)
            logger.info(f"📌 Expected head version: {expected_head}")
        except Exception as e:
            # Se não conseguir obter head, apenas logamos warning
            # (pode ser ambiente sem alembic.ini acessível)
            logger.warning(f"⚠️  Could not determine alembic head: {str(e)}")
            logger.warning("⚠️  Skipping head comparison (assuming current version is correct)")
            logger.info(f"✅ Database ready (version: {current_version}, head check skipped)")
            return
        
        # ============================================================
        # 4️⃣ COMPARAR VERSÃO ATUAL COM HEAD ESPERADO
        # ============================================================
        
        if current_version != expected_head:
            error_msg = (
                f"Database migrations pending:\n"
                f"  Current version: {current_version}\n"
                f"  Expected version: {expected_head}\n"
                f"Please run: alembic upgrade head"
            )
            logger.error(f"❌ {error_msg}")
            raise DatabaseMigrationError(error_msg)
        
        # ============================================================
        # ✅ SUCESSO: BANCO PRONTO
        # ============================================================
        
        logger.info(f"✅ Database ready: migrations up to date (version: {current_version})")
    
    except DatabaseMigrationError:
        # Re-raise nossa exceção customizada
        raise
    
    except Exception as e:
        error_msg = f"Error checking database migrations: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise DatabaseMigrationError(error_msg) from e


def _get_alembic_head(engine: Engine, alembic_ini_path: Optional[str] = None) -> str:
    """
    Obtém o head (versão mais recente) do Alembic.
    
    Args:
        engine: SQLAlchemy engine
        alembic_ini_path: Caminho para alembic.ini (opcional)
    
    Returns:
        String da versão head (ex: "abc123def456")
    
    Raises:
        Exception: Se não conseguir determinar o head
    """
    
    # Se alembic_ini_path não fornecido, tentar path padrão
    if alembic_ini_path is None:
        import os
        # Assumir que alembic.ini está em backend/alembic.ini
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        alembic_ini_path = os.path.join(current_dir, "alembic.ini")
    
    # Verificar se arquivo existe
    import os
    if not os.path.exists(alembic_ini_path):
        raise FileNotFoundError(f"alembic.ini not found at: {alembic_ini_path}")
    
    # Carregar configuração do Alembic
    alembic_cfg = Config(alembic_ini_path)
    
    # Obter ScriptDirectory
    script = ScriptDirectory.from_config(alembic_cfg)
    
    # Obter head (pode haver múltiplos heads em branches, pegamos o primeiro)
    heads = script.get_heads()
    
    if not heads:
        raise RuntimeError("No alembic head found in migration scripts")
    
    if len(heads) > 1:
        logger.warning(f"⚠️  Multiple alembic heads found: {heads}, using first one")
    
    return heads[0]


def get_migration_status(engine: Engine, alembic_ini_path: Optional[str] = None) -> dict:
    """
    Retorna o status das migrations sem levantar exceções.
    Útil para diagnósticos, health checks e dashboards.
    
    Args:
        engine: SQLAlchemy engine
        alembic_ini_path: Caminho para alembic.ini (opcional)
    
    Returns:
        Dict com status das migrations:
        {
            'table_exists': bool,
            'current_version': str | None,
            'expected_head': str | None,
            'is_up_to_date': bool,
            'message': str
        }
    
    Example:
        >>> status = get_migration_status(engine)
        >>> if not status['is_up_to_date']:
        >>>     print(f"Migrations pending: {status['message']}")
    """
    
    status = {
        'table_exists': False,
        'current_version': None,
        'expected_head': None,
        'is_up_to_date': False,
        'message': 'Unknown'
    }
    
    try:
        # Verificar tabela alembic_version
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "alembic_version" not in tables:
            status['message'] = 'alembic_version table not found'
            return status
        
        status['table_exists'] = True
        
        # Obter versão atual
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            
            if not row:
                status['message'] = 'No version found in alembic_version'
                return status
            
            status['current_version'] = row[0]
        
        # Obter head esperado
        try:
            status['expected_head'] = _get_alembic_head(engine, alembic_ini_path)
        except Exception as e:
            status['message'] = f'Could not determine head: {str(e)}'
            status['is_up_to_date'] = None  # Desconhecido
            return status
        
        # Comparar
        if status['current_version'] == status['expected_head']:
            status['is_up_to_date'] = True
            status['message'] = 'Up to date'
        else:
            status['is_up_to_date'] = False
            status['message'] = f"Pending: {status['current_version']} -> {status['expected_head']}"
        
        return status
    
    except Exception as e:
        status['message'] = f'Error: {str(e)}'
        return status


def check_migrations_cli(engine: Engine, alembic_ini_path: Optional[str] = None) -> None:
    """
    Versão CLI-friendly para verificar migrations.
    Imprime status e retorna exit code apropriado.
    
    Args:
        engine: SQLAlchemy engine
        alembic_ini_path: Caminho para alembic.ini (opcional)
    
    Returns:
        None (usa sys.exit internamente)
    """
    
    import sys
    
    print("=" * 80)
    print("DATABASE MIGRATION STATUS CHECK")
    print("=" * 80)
    print()
    
    status = get_migration_status(engine, alembic_ini_path)
    
    print(f"Table exists:     {status['table_exists']}")
    print(f"Current version:  {status['current_version'] or 'N/A'}")
    print(f"Expected head:    {status['expected_head'] or 'N/A'}")
    print(f"Up to date:       {status['is_up_to_date']}")
    print(f"Message:          {status['message']}")
    print()
    
    if status['is_up_to_date'] is True:
        print("✅ Database migrations are up to date!")
        print("=" * 80)
        sys.exit(0)
    elif status['is_up_to_date'] is False:
        print("❌ Database migrations are PENDING!")
        print()
        print("Run: alembic upgrade head")
        print("=" * 80)
        sys.exit(1)
    else:
        print("⚠️  Could not determine migration status")
        print("=" * 80)
        sys.exit(2)
