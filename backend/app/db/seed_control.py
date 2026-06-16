"""
Seed Control - Pré-Prod Bloco 5
================================

Controle de execução de seed de dados iniciais para garantir:

1. Seed roda UMA única vez
2. Seed é idempotente (pode rodar múltiplas vezes sem problemas)
3. Produção NÃO é contaminada automaticamente
4. DEV/TEST continuam fáceis de usar

Estratégia Escolhida: Tabela seed_version
------------------------------------------

A tabela `seed_version` armazena registro de seeds aplicados:
- seed_name: Nome do seed (ex: "initial_data", "roles_permissions")
- applied_at: Timestamp de quando foi aplicado
- applied_by: Quem aplicou (sistema, usuário, CI/CD)

Vantagens:
- Simples e direto
- Fácil de consultar e auditar
- Suporta múltiplos seeds nomeados
- Facilita versionamento de seeds

Autor: Sistema Pet - Pré-Prod Block 5
Data: 2026-02-05
"""

import logging
from typing import Optional, Callable
from datetime import datetime
from sqlalchemy import Table, Column, String, DateTime, MetaData, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINIÇÃO DA TABELA seed_version
# ============================================================================

metadata = MetaData()

seed_version_table = Table(
    "seed_version",
    metadata,
    Column("seed_name", String(100), primary_key=True),
    Column("applied_at", DateTime, nullable=False),
    Column("applied_by", String(100), nullable=False, default="system"),
)


# ============================================================================
# CONTROLE DE SEED
# ============================================================================


def ensure_seed_version_table(session: Session) -> None:
    """
    Garante que a tabela seed_version existe.

    Cria a tabela se ela não existir. Idempotente.

    Args:
        session: SQLAlchemy session

    Raises:
        Exception: Se não conseguir criar a tabela
    """
    try:
        # Verificar se tabela existe
        result = session.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.tables "
                "  WHERE table_name = 'seed_version'"
                ")"
            )
        )
        exists = result.scalar()

        if not exists:
            logger.info("📋 Creating seed_version table...")

            # Criar tabela
            metadata.create_all(session.bind, tables=[seed_version_table])
            session.commit()

            logger.info("✅ seed_version table created successfully")
        else:
            logger.debug("✓ seed_version table already exists")

    except Exception as e:
        logger.error(f"❌ Error ensuring seed_version table: {str(e)}")
        session.rollback()
        raise


def is_seed_applied(session: Session, seed_name: str = "initial_data") -> bool:
    """
    Verifica se um seed específico já foi aplicado.

    Args:
        session: SQLAlchemy session
        seed_name: Nome do seed a verificar (default: "initial_data")

    Returns:
        True se seed já foi aplicado, False caso contrário

    Example:
        >>> if not is_seed_applied(session):
        >>>     apply_initial_seed(session)
    """
    try:
        # Garantir que tabela existe
        ensure_seed_version_table(session)

        # Verificar se seed já foi aplicado
        result = session.execute(
            text("SELECT COUNT(*) FROM seed_version WHERE seed_name = :name"),
            {"name": seed_name},
        )
        count = result.scalar()

        applied = count > 0

        if applied:
            logger.info(f"✓ Seed '{seed_name}' already applied")
        else:
            logger.info(f"○ Seed '{seed_name}' not yet applied")

        return applied

    except Exception as e:
        logger.error(f"❌ Error checking seed status: {str(e)}")
        # Em caso de erro, assumir que seed NÃO foi aplicado
        # (mais seguro do que assumir que foi)
        return False


def mark_seed_as_applied(
    session: Session, seed_name: str = "initial_data", applied_by: str = "system"
) -> None:
    """
    Marca um seed como aplicado.

    Args:
        session: SQLAlchemy session
        seed_name: Nome do seed
        applied_by: Quem aplicou (system, admin, CI/CD, etc.)

    Raises:
        Exception: Se não conseguir marcar seed
    """
    try:
        # Garantir que tabela existe
        ensure_seed_version_table(session)

        # Inserir registro
        session.execute(
            text(
                "INSERT INTO seed_version (seed_name, applied_at, applied_by) "
                "VALUES (:name, :applied_at, :applied_by)"
            ),
            {
                "name": seed_name,
                "applied_at": datetime.utcnow(),
                "applied_by": applied_by,
            },
        )
        session.commit()

        logger.info(f"✅ Seed '{seed_name}' marked as applied by {applied_by}")

    except Exception as e:
        logger.error(f"❌ Error marking seed as applied: {str(e)}")
        session.rollback()
        raise


def seed_if_needed(
    session: Session,
    seed_func: Callable[[Session], None],
    seed_name: str = "initial_data",
    force: bool = False,
) -> bool:
    """
    Executa seed inicial apenas se ainda não foi executado.

    Esta é a função PRINCIPAL para aplicar seeds de forma controlada.

    Args:
        session: SQLAlchemy session
        seed_func: Função que aplica o seed (recebe session)
        seed_name: Nome do seed (para tracking)
        force: Se True, aplica mesmo se já foi aplicado (use com cuidado!)

    Returns:
        True se seed foi aplicado, False se já estava aplicado

    Raises:
        Exception: Se seed falhar

    Example:
        >>> def apply_initial_data(session):
        >>>     # Criar roles
        >>>     session.add(Role(name="admin"))
        >>>     session.commit()
        >>>
        >>> seed_if_needed(session, apply_initial_data, seed_name="initial_roles")

    Fluxo de execução:
    ------------------
    1. Verifica se seed já foi aplicado (via is_seed_applied)
    2. Se JÁ aplicado e force=False: retorna False (não faz nada)
    3. Se NÃO aplicado ou force=True:
       a. Executa seed_func(session)
       b. Marca seed como aplicado (via mark_seed_as_applied)
       c. Retorna True
    """

    logger.info(f"🌱 Checking seed: {seed_name}")

    # Verificar se já foi aplicado
    already_applied = is_seed_applied(session, seed_name)

    if already_applied and not force:
        logger.info(f"⏭️  Seed '{seed_name}' already applied, skipping...")
        return False

    if already_applied and force:
        logger.warning(f"⚠️  FORCE mode enabled: re-applying seed '{seed_name}'")

    # Aplicar seed
    try:
        logger.info(f"🌱 Applying seed: {seed_name}")

        # Executar função de seed
        seed_func(session)

        # Marcar como aplicado (se não estiver forçando re-aplicação)
        if not already_applied:
            mark_seed_as_applied(session, seed_name, applied_by="system")

        logger.info(f"✅ Seed '{seed_name}' applied successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Error applying seed '{seed_name}': {str(e)}")
        session.rollback()
        raise


# ============================================================================
# FUNÇÕES DE UTILIDADE
# ============================================================================


def list_applied_seeds(session: Session) -> list[dict]:
    """
    Lista todos os seeds que já foram aplicados.

    Args:
        session: SQLAlchemy session

    Returns:
        Lista de dicts com: seed_name, applied_at, applied_by

    Example:
        >>> seeds = list_applied_seeds(session)
        >>> for seed in seeds:
        >>>     print(f"{seed['seed_name']} applied at {seed['applied_at']}")
    """
    try:
        ensure_seed_version_table(session)

        result = session.execute(
            text(
                "SELECT seed_name, applied_at, applied_by FROM seed_version ORDER BY applied_at"
            )
        )

        seeds = [
            {"seed_name": row[0], "applied_at": row[1], "applied_by": row[2]}
            for row in result
        ]

        return seeds

    except Exception as e:
        logger.error(f"❌ Error listing seeds: {str(e)}")
        return []


def reset_seed(session: Session, seed_name: str) -> None:
    """
    Remove o registro de um seed, permitindo que ele seja reaplicado.

    ⚠️  USO CUIDADOSO! Isso NÃO desfaz as mudanças do seed, apenas
    remove o registro de que ele foi aplicado.

    Args:
        session: SQLAlchemy session
        seed_name: Nome do seed a resetar

    Example:
        >>> # Em DEV, se quiser re-aplicar seed
        >>> reset_seed(session, "initial_data")
        >>> seed_if_needed(session, apply_initial_data)
    """
    try:
        ensure_seed_version_table(session)

        session.execute(
            text("DELETE FROM seed_version WHERE seed_name = :name"),
            {"name": seed_name},
        )
        session.commit()

        logger.warning(f"⚠️  Seed '{seed_name}' reset (can be re-applied now)")

    except Exception as e:
        logger.error(f"❌ Error resetting seed: {str(e)}")
        session.rollback()
        raise


def get_seed_info(session: Session, seed_name: str) -> Optional[dict]:
    """
    Obtém informações sobre um seed específico.

    Args:
        session: SQLAlchemy session
        seed_name: Nome do seed

    Returns:
        Dict com info do seed ou None se não aplicado

    Example:
        >>> info = get_seed_info(session, "initial_data")
        >>> if info:
        >>>     print(f"Applied at: {info['applied_at']}")
    """
    try:
        ensure_seed_version_table(session)

        result = session.execute(
            text(
                "SELECT seed_name, applied_at, applied_by "
                "FROM seed_version "
                "WHERE seed_name = :name"
            ),
            {"name": seed_name},
        )

        row = result.fetchone()

        if row:
            return {"seed_name": row[0], "applied_at": row[1], "applied_by": row[2]}

        return None

    except Exception as e:
        logger.error(f"❌ Error getting seed info: {str(e)}")
        return None


# ============================================================================
# CONTROLE DE AMBIENTE
# ============================================================================


def should_run_seed(env: str, allow_prod_seed: bool = False) -> bool:
    """
    Determina se seed deve ser executado baseado no ambiente.

    Regras:
    -------
    - DEV: Sempre pode rodar seed
    - TEST: Sempre pode rodar seed
    - PROD: Apenas se allow_prod_seed=True (flag explícita)

    Args:
        env: Ambiente atual (development, test, production)
        allow_prod_seed: Flag explícita para permitir seed em produção

    Returns:
        True se seed pode ser executado, False caso contrário

    Example:
        >>> from app.config import ENVIRONMENT
        >>> if should_run_seed(ENVIRONMENT):
        >>>     seed_if_needed(session, apply_initial_data)
    """
    env_lower = env.lower()

    if env_lower in ["development", "dev"]:
        logger.info("✅ Environment: DEV - seed allowed")
        return True

    if env_lower in ["test", "testing"]:
        logger.info("✅ Environment: TEST - seed allowed")
        return True

    if env_lower in ["production", "prod"]:
        if allow_prod_seed:
            logger.warning("⚠️  Environment: PROD - seed EXPLICITLY ALLOWED")
            return True
        else:
            logger.warning(
                "❌ Environment: PROD - seed BLOCKED (use allow_prod_seed=True to override)"
            )
            return False

    # Ambiente desconhecido - bloquear por segurança
    logger.warning(f"❌ Environment: {env} - unknown, seed BLOCKED")
    return False


# ============================================================================
# WRAPPER DE CONVENIÊNCIA
# ============================================================================


def run_seed_safely(
    session: Session,
    seed_func: Callable[[Session], None],
    seed_name: str = "initial_data",
    env: Optional[str] = None,
    allow_prod: bool = False,
    force: bool = False,
) -> bool:
    """
    Wrapper de alto nível que combina todas as verificações de segurança.

    Esta função:
    1. Verifica ambiente (DEV/TEST/PROD)
    2. Verifica se seed já foi aplicado
    3. Aplica seed de forma controlada

    Args:
        session: SQLAlchemy session
        seed_func: Função que aplica o seed
        seed_name: Nome do seed
        env: Ambiente (se None, não verifica)
        allow_prod: Flag para permitir em produção
        force: Flag para forçar re-aplicação

    Returns:
        True se seed foi aplicado, False caso contrário

    Example:
        >>> from app.config import ENVIRONMENT
        >>> from app.db import get_session
        >>>
        >>> def apply_my_seed(session):
        >>>     # ... criar dados iniciais ...
        >>>     pass
        >>>
        >>> session = next(get_session())
        >>> run_seed_safely(
        >>>     session,
        >>>     apply_my_seed,
        >>>     seed_name="my_seed",
        >>>     env=ENVIRONMENT
        >>> )
    """

    # Verificar ambiente
    if env is not None:
        if not should_run_seed(env, allow_prod_seed=allow_prod):
            logger.warning(f"🚫 Seed '{seed_name}' blocked by environment policy")
            return False

    # Aplicar seed se necessário
    return seed_if_needed(session, seed_func, seed_name, force=force)
