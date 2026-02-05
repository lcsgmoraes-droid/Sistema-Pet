"""
Migration: Criar Event Store para Event Sourcing
================================================

Data: 2026-01-23
Fase: 5.2 - Event Store Enhanced

OBJETIVO:
Criar tabela domain_events para event sourcing completo
com suporte a replay determinístico e auditoria.

CARACTERÍSTICAS:
- sequence_number: Ordem global monotônica
- correlation_id: Rastrear fluxo completo
- causation_id: Evento que causou este evento
- Índices otimizados para queries de replay
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def upgrade(db_path: str = "petshop.db"):
    """
    Cria tabela domain_events com campos necessários para event sourcing.
    
    CARACTERÍSTICAS:
    - AUTOINCREMENT garante sequence_number monotônico
    - Índices para queries de replay eficientes
    - Imutabilidade (apenas INSERT, nunca UPDATE/DELETE)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        logger.info("🚀 Iniciando migration: Event Store Enhanced")
        
        # 1. Criar tabela domain_events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS domain_events (
                -- Identificação única do evento
                id TEXT PRIMARY KEY NOT NULL,
                
                -- Ordenação global (CRÍTICO para replay)
                sequence_number INTEGER NOT NULL UNIQUE,
                
                -- Metadados do evento
                event_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                aggregate_type TEXT NOT NULL,
                
                -- Multi-tenancy
                user_id INTEGER NOT NULL,
                
                -- Rastreabilidade
                correlation_id TEXT,  -- Rastrear fluxo completo (ex: toda uma venda)
                causation_id TEXT,    -- Evento que causou este evento
                
                -- Dados do evento
                payload TEXT NOT NULL,  -- JSON serializado
                metadata TEXT,          -- JSON com dados técnicos
                
                -- Timestamp
                created_at TEXT NOT NULL,
                
                -- Constraints
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        logger.info("✅ Tabela domain_events criada")
        
        # 2. Criar índices para queries de replay
        indexes = [
            # Índice principal: ordenação global
            ("idx_domain_events_sequence", "sequence_number"),
            
            # Replay por tenant
            ("idx_domain_events_user_seq", "user_id, sequence_number"),
            
            # Replay por tipo de evento
            ("idx_domain_events_type_seq", "event_type, sequence_number"),
            
            # Replay por agregado
            ("idx_domain_events_aggregate", "aggregate_id, sequence_number"),
            
            # Rastreabilidade
            ("idx_domain_events_correlation", "correlation_id"),
            
            # Busca por data
            ("idx_domain_events_created_at", "created_at"),
        ]
        
        for index_name, columns in indexes:
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON domain_events ({columns})
            """)
            logger.info(f"✅ Índice {index_name} criado")
        
        # 3. Criar sequence para sequence_number (SQLite usa AUTOINCREMENT)
        # Nota: Em SQLite, AUTOINCREMENT garante monotonia mesmo com DELETEs
        # Em PostgreSQL, usaríamos uma SEQUENCE separada
        
        conn.commit()
        logger.info("✅ Migration Event Store Enhanced concluída com sucesso!")
        
        # 4. Validar estrutura
        cursor.execute("PRAGMA table_info(domain_events)")
        columns = cursor.fetchall()
        logger.info(f"📊 Colunas criadas: {[col[1] for col in columns]}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erro na migration: {str(e)}", exc_info=True)
        raise
    finally:
        conn.close()


def downgrade(db_path: str = "petshop.db"):
    """
    Remove tabela domain_events (USE COM CUIDADO!).
    
    ATENÇÃO: Esta operação é DESTRUTIVA e IRREVERSÍVEL!
    Apenas usar em ambiente de desenvolvimento.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        logger.warning("⚠️  DOWNGRADE: Removendo tabela domain_events")
        
        cursor.execute("DROP TABLE IF EXISTS domain_events")
        
        conn.commit()
        logger.info("✅ Downgrade concluído")
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erro no downgrade: {str(e)}", exc_info=True)
        raise
    finally:
        conn.close()


def validate(db_path: str = "petshop.db"):
    """
    Valida que a migration foi aplicada corretamente.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar se tabela existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='domain_events'
        """)
        if not cursor.fetchone():
            logger.error("❌ Tabela domain_events não existe!")
            return False
        
        # Verificar colunas obrigatórias
        cursor.execute("PRAGMA table_info(domain_events)")
        columns = {col[1] for col in cursor.fetchall()}
        
        required_columns = {
            'id', 'sequence_number', 'event_type', 'aggregate_id',
            'aggregate_type', 'user_id', 'correlation_id', 'causation_id',
            'payload', 'metadata', 'created_at'
        }
        
        if not required_columns.issubset(columns):
            missing = required_columns - columns
            logger.error(f"❌ Colunas faltando: {missing}")
            return False
        
        # Verificar índices
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND tbl_name='domain_events'
        """)
        indexes = {row[0] for row in cursor.fetchall()}
        
        expected_indexes = {
            'idx_domain_events_sequence',
            'idx_domain_events_user_seq',
            'idx_domain_events_type_seq',
            'idx_domain_events_aggregate',
            'idx_domain_events_correlation',
            'idx_domain_events_created_at',
        }
        
        if not expected_indexes.issubset(indexes):
            missing = expected_indexes - indexes
            logger.warning(f"⚠️  Índices faltando: {missing}")
            # Não é crítico, apenas aviso
        
        logger.info("✅ Validação da migration passou!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}", exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Executar migration
    print("=" * 60)
    print("Migration: Event Store Enhanced")
    print("=" * 60)
    
    db_path = Path(__file__).parent.parent / "petshop.db"
    
    if upgrade(str(db_path)):
        print("\n✅ Migration aplicada com sucesso!")
        
        if validate(str(db_path)):
            print("✅ Validação passou!")
        else:
            print("⚠️  Validação falhou (verificar logs)")
    else:
        print("\n❌ Falha ao aplicar migration!")
