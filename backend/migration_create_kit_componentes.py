"""
Migration: Criar tabela produto_kit_componentes
Sprint 4 - Passo 2 - Parte 2

Cria a tabela para relacionamento de componentes de produtos KIT.
Permite definir quais produtos compõem um KIT e suas quantidades.

Data: 2026-01-24
"""

import sqlite3
from datetime import datetime
import os

# Caminho do banco
DB_PATH = os.path.join(os.path.dirname(__file__), 'petshop.db')

def executar_migration():
    """Cria tabela produto_kit_componentes"""
    
    print("=" * 60)
    print("MIGRATION: Criar tabela produto_kit_componentes")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Verificar se a tabela já existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='produto_kit_componentes'
        """)
        
        if cursor.fetchone():
            print("✓ Tabela produto_kit_componentes já existe. Migration já executada.")
            conn.close()
            return
        
        # 2. Criar tabela produto_kit_componentes
        print("\n1. Criando tabela produto_kit_componentes...")
        cursor.execute("""
            CREATE TABLE produto_kit_componentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kit_id INTEGER NOT NULL,
                produto_componente_id INTEGER NOT NULL,
                quantidade REAL NOT NULL DEFAULT 1.0,
                opcional INTEGER DEFAULT 0,
                ordem INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (kit_id) REFERENCES produtos(id) ON DELETE CASCADE,
                FOREIGN KEY (produto_componente_id) REFERENCES produtos(id),
                
                -- Garantir que não haja componentes duplicados no mesmo KIT
                UNIQUE(kit_id, produto_componente_id)
            )
        """)
        
        # 3. Criar índices para performance
        print("2. Criando índices...")
        
        cursor.execute("""
            CREATE INDEX idx_kit_componentes_kit 
            ON produto_kit_componentes(kit_id)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_kit_componentes_produto 
            ON produto_kit_componentes(produto_componente_id)
        """)
        
        # 4. Verificar estrutura criada
        cursor.execute("PRAGMA table_info(produto_kit_componentes)")
        colunas = cursor.fetchall()
        
        print(f"\n✓ Tabela criada com {len(colunas)} colunas:")
        for col in colunas:
            print(f"  - {col[1]} ({col[2]})")
        
        # 5. Verificar índices
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND tbl_name='produto_kit_componentes'
        """)
        indices = cursor.fetchall()
        
        print(f"\n✓ Índices criados ({len(indices)}):")
        for idx in indices:
            print(f"  - {idx[0]}")
        
        # 6. Commit
        conn.commit()
        print("\n✓ Migration concluída com sucesso!")
        print("\nTabela produto_kit_componentes pronta para uso!")
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n✗ ERRO na migration: {e}")
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    executar_migration()
    print("\n" + "=" * 60)
    print("SPRINT 4 - PASSO 2 - PARTE 2: CONCLUÍDO")
    print("=" * 60)
