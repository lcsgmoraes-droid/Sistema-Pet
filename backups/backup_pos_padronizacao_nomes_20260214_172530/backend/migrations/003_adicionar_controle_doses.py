"""
Migração para adicionar campos de controle de doses
Data: 2026-01-13
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def adicionar_campos_doses():
    """Adicionar campos de controle de doses"""
    try:
        with engine.connect() as conn:
            # Verificar colunas existentes
            result = conn.execute(text("PRAGMA table_info(produtos)"))
            colunas_produtos = [row[1] for row in result]
            
            result = conn.execute(text("PRAGMA table_info(lembretes)"))
            colunas_lembretes = [row[1] for row in result]
            
            # Adicionar em produtos
            if 'numero_doses' not in colunas_produtos:
                logger.info("📝 Adicionando coluna numero_doses em produtos...")
                conn.execute(text("ALTER TABLE produtos ADD COLUMN numero_doses INTEGER"))
                conn.commit()
                logger.info("✅ Coluna numero_doses adicionada!")
            else:
                logger.info("ℹ️  Coluna numero_doses já existe em produtos")
            
            # Adicionar em lembretes
            campos_lembretes = [
                ("dose_atual", "ALTER TABLE lembretes ADD COLUMN dose_atual INTEGER DEFAULT 1"),
                ("dose_total", "ALTER TABLE lembretes ADD COLUMN dose_total INTEGER"),
                ("historico_doses", "ALTER TABLE lembretes ADD COLUMN historico_doses TEXT")
            ]
            
            for campo_nome, sql_comando in campos_lembretes:
                if campo_nome not in colunas_lembretes:
                    logger.info(f"📝 Adicionando coluna: {campo_nome} em lembretes")
                    conn.execute(text(sql_comando))
                    conn.commit()
                    logger.info(f"✅ Coluna {campo_nome} adicionada!")
                else:
                    logger.info(f"ℹ️  Coluna {campo_nome} já existe em lembretes")
            
            logger.info(f"\n✅ Migração de controle de doses concluída!")
        
        return True
            
    except Exception as e:
        logger.error(f"❌ Erro na migração: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    sucesso = adicionar_campos_doses()
    sys.exit(0 if sucesso else 1)
