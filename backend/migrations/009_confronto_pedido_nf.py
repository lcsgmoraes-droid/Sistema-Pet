"""
Migração: Adicionar campos de confronto Pedido x NF na tabela pedidos_compra
Data: 2026-04-15
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def adicionar_campos_confronto():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(pedidos_compra)"))
            colunas_existentes = [row[1] for row in result]

            campos_novos = [
                ("nota_entrada_id", "ALTER TABLE pedidos_compra ADD COLUMN nota_entrada_id INTEGER REFERENCES notas_entrada(id)"),
                ("data_confronto", "ALTER TABLE pedidos_compra ADD COLUMN data_confronto DATETIME"),
                ("status_confronto", "ALTER TABLE pedidos_compra ADD COLUMN status_confronto VARCHAR(30)"),
                ("resumo_confronto", "ALTER TABLE pedidos_compra ADD COLUMN resumo_confronto TEXT"),
            ]

            for campo_nome, sql in campos_novos:
                if campo_nome not in colunas_existentes:
                    logger.info(f"📝 Adicionando coluna: {campo_nome}")
                    conn.execute(text(sql))
                    conn.commit()
                    logger.info(f"✅ Coluna {campo_nome} adicionada!")
                else:
                    logger.info(f"⏭️  Coluna {campo_nome} já existe.")

        logger.info("✅ Migração 009 concluída!")
    except Exception as e:
        logger.error(f"❌ Erro na migração: {e}")
        raise


if __name__ == "__main__":
    adicionar_campos_confronto()
