"""
Migration: Adicionar campo tipo_kit na tabela produtos
Sprint 4 - Passo 2 - Parte 1

Adiciona o campo tipo_kit para diferenciar KITs VIRTUAL e FISICO:
- VIRTUAL: Custo calculado pela soma dos componentes
- FISICO: Custo próprio do KIT (pré-montado/embalado)

Data: 2026-01-24
"""

import sqlite3
from datetime import datetime
import os

# Caminho do banco
DB_PATH = os.path.join(os.path.dirname(__file__), 'petshop.db')

def executar_migration():
    """Adiciona campo tipo_kit na tabela produtos"""
    
    print("=" * 60)
    print("MIGRATION: Adicionar campo tipo_kit")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(produtos)")
        colunas = [col[1] for col in cursor.fetchall()]
        
        if 'tipo_kit' in colunas:
            print("✓ Campo tipo_kit já existe. Migration já executada.")
            conn.close()
            return
        
        # 2. Adicionar coluna tipo_kit
        print("\n1. Adicionando coluna tipo_kit...")
        cursor.execute("""
            ALTER TABLE produtos 
            ADD COLUMN tipo_kit VARCHAR(20) DEFAULT 'VIRTUAL'
        """)
        
        # 3. Atualizar valores existentes
        print("2. Definindo valores padrão...")
        cursor.execute("""
            UPDATE produtos 
            SET tipo_kit = 'VIRTUAL'
            WHERE tipo_kit IS NULL
        """)
        
        # 4. Verificar resultados
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN tipo_produto = 'KIT' THEN 1 ELSE 0 END) as kits,
                   SUM(CASE WHEN tipo_kit = 'VIRTUAL' THEN 1 ELSE 0 END) as virtuais
            FROM produtos
        """)
        
        total, kits, virtuais = cursor.fetchone()
        
        print(f"\n✓ Campo tipo_kit adicionado com sucesso!")
        print(f"  - Total de produtos: {total}")
        print(f"  - Produtos tipo KIT: {kits}")
        print(f"  - Com tipo_kit VIRTUAL: {virtuais}")
        
        # 5. Commit
        conn.commit()
        print("\n✓ Migration concluída com sucesso!")
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n✗ ERRO na migration: {e}")
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    executar_migration()
    print("\n" + "=" * 60)
    print("SPRINT 4 - PASSO 2 - PARTE 1: CONCLUÍDO")
    print("=" * 60)
