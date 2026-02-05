"""
Migração: Adicionar coluna data_cancelamento na tabela vendas

Esta migração adiciona o campo data_cancelamento para suportar
o fluxo de cancelamento atômico implementado no Sprint 3.

EXECUTAR ANTES DE INICIAR O BACKEND!

Uso:
    python migracao_data_cancelamento.py
"""

import sqlite3
from datetime import datetime

def migrar():
    """Adiciona coluna data_cancelamento se não existir"""
    import os
    
    # Tentar diferentes localizações do banco
    db_paths = [
        'petshop.db',  # Prioridade 1
        'app/petshop.db',
        'app/sistema.db',
        'sistema.db'
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Banco de dados não encontrado!")
        print("Locais verificados:")
        for path in db_paths:
            print(f"  - {path}")
        return
    
    print(f"📂 Usando banco: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(vendas)")
        colunas = [col[1] for col in cursor.fetchall()]
        
        if 'data_cancelamento' not in colunas:
            print("📋 Adicionando coluna data_cancelamento...")
            cursor.execute("""
                ALTER TABLE vendas 
                ADD COLUMN data_cancelamento DATETIME NULL
            """)
            conn.commit()
            print("✅ Coluna data_cancelamento adicionada com sucesso!")
            
            # Atualizar vendas já canceladas com a data de updated_at
            cursor.execute("""
                UPDATE vendas 
                SET data_cancelamento = updated_at 
                WHERE status = 'cancelada' AND data_cancelamento IS NULL
            """)
            conn.commit()
            
            vendas_atualizadas = cursor.rowcount
            if vendas_atualizadas > 0:
                print(f"📝 {vendas_atualizadas} venda(s) cancelada(s) anteriormente atualizada(s)")
        else:
            print("⚠️  Coluna data_cancelamento já existe. Nenhuma alteração necessária.")
    
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    print("\n" + "="*80)
    print("MIGRAÇÃO: Adicionar data_cancelamento na tabela vendas")
    print("="*80 + "\n")
    
    migrar()
    
    print("\n" + "="*80)
    print("✅ Migração concluída!")
    print("="*80 + "\n")
