"""
Script para executar migrations SQL no banco de dados
"""
import sqlite3
import os
from app.utils.logger import logger

# Caminho do banco de dados
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database.db')

# Caminho do arquivo de migration
MIGRATION_FILE = os.path.join(os.path.dirname(__file__), 'create_cliente_timeline_view.sql')

def run_migration():
    """Executa a migration SQL"""
    logger.info("🔧 Conectando ao banco de dados...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    logger.info("📄 Lendo arquivo de migration...")
    with open(MIGRATION_FILE, 'r', encoding='utf-8') as f:
        sql_commands = f.read()
    
    logger.info("⚙️ Executando comandos SQL...")
    try:
        cursor.executescript(sql_commands)
        conn.commit()
        logger.info("✅ Migration executada com sucesso!")
        
        # Verificar se a view foi criada
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='cliente_timeline'")
        result = cursor.fetchone()
        
        if result:
            logger.info(f"✅ View '{result[0]}' criada com sucesso!")
            
            # Contar registros na view (se houver dados)
            cursor.execute("SELECT COUNT(*) FROM cliente_timeline")
            count = cursor.fetchone()[0]
            logger.info(f"📊 Total de eventos na timeline: {count}")
        else:
            logger.warning("⚠️ View não foi encontrada após execução")
            
    except Exception as e:
        logger.info(f"❌ Erro ao executar migration: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        logger.info("🔌 Conexão fechada")

if __name__ == '__main__':
    run_migration()
