"""
Migração 010 — Adiciona coluna confronto_finalizado em pedidos_compra
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def run(db_session):
    """Adiciona confronto_finalizado BOOLEAN DEFAULT FALSE à tabela pedidos_compra."""
    try:
        db_session.execute(text("""
            ALTER TABLE pedidos_compra
            ADD COLUMN IF NOT EXISTS confronto_finalizado BOOLEAN DEFAULT FALSE
        """))
        db_session.commit()
        logger.info("Migração 010: coluna confronto_finalizado adicionada com sucesso.")
    except Exception as e:
        db_session.rollback()
        logger.error(f"Migração 010 falhou: {e}")
        raise
