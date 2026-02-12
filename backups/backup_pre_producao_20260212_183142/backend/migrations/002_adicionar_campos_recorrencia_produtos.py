"""
Migração para adicionar campos de recorrência na tabela produtos
Data: 2026-01-13
"""

import sys
from pathlib import Path

# Adicionar o diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def adicionar_campos_recorrencia():
    """Adicionar campos de recorrência à tabela produtos"""
    try:
        with engine.connect() as conn:
            # Verificar se as colunas já existem
            result = conn.execute(text("PRAGMA table_info(produtos)"))
            colunas_existentes = [row[1] for row in result]
            
            campos_novos = [
                ("tem_recorrencia", "ALTER TABLE produtos ADD COLUMN tem_recorrencia BOOLEAN DEFAULT 0"),
                ("tipo_recorrencia", "ALTER TABLE produtos ADD COLUMN tipo_recorrencia VARCHAR(20)"),
                ("intervalo_dias", "ALTER TABLE produtos ADD COLUMN intervalo_dias INTEGER"),
                ("observacoes_recorrencia", "ALTER TABLE produtos ADD COLUMN observacoes_recorrencia TEXT"),
                ("especie_compativel", "ALTER TABLE produtos ADD COLUMN especie_compativel VARCHAR(50)")
            ]
            
            for campo_nome, sql_comando in campos_novos:
                if campo_nome not in colunas_existentes:
                    logger.info(f"📝 Adicionando coluna: {campo_nome}")
                    conn.execute(text(sql_comando))
                    conn.commit()
                    logger.info(f"✅ Coluna {campo_nome} adicionada!")
                else:
                    logger.info(f"ℹ️  Coluna {campo_nome} já existe")
            
            # Verificar resultado final
            result = conn.execute(text("PRAGMA table_info(produtos)"))
            colunas_finais = [row[1] for row in result]
            
            logger.info(f"\n✅ Migração concluída!")
            logger.info(f"Total de colunas na tabela produtos: {len(colunas_finais)}")
            
            # Verificar se todos os campos foram adicionados
            for campo_nome, _ in campos_novos:
                if campo_nome in colunas_finais:
                    logger.info(f"  ✓ {campo_nome}")
                else:
                    logger.error(f"  ✗ {campo_nome} - FALTANDO!")
        
        return True
            
    except Exception as e:
        logger.error(f"❌ Erro na migração: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    sucesso = adicionar_campos_recorrencia()
    sys.exit(0 if sucesso else 1)
