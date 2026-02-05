"""
Migration 008: Adicionar Constraints de Idempotência nos Read Models
=====================================================================

OBJETIVO:
Adicionar UNIQUE constraints nas chaves de idempotência para garantir
que UPSERT funcione corretamente.

CHAVES DE IDEMPOTÊNCIA:
- read_vendas_resumo_diario: UNIQUE (data)
- read_performance_parceiro: UNIQUE (funcionario_id, mes_referencia)
- read_receita_mensal: UNIQUE (mes_referencia)

FASE: 5.3 - Handlers Idempotentes
"""

import sqlite3
from pathlib import Path


def aplicar_migration():
    """Aplica a migration adicionando constraints de idempotência"""
    
    db_path = Path(__file__).parent.parent / "petshop.db"
    
    if not db_path.exists():
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        print("🚀 Iniciando Migration 008: Constraints de Idempotência")
        print()
        
        # =====================================================================
        # 1. read_vendas_resumo_diario: UNIQUE (data)
        # =====================================================================
        
        print("1️⃣ Adicionando UNIQUE constraint em read_vendas_resumo_diario.data...")
        
        # Verificar se já existe
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='index' AND tbl_name='read_vendas_resumo_diario'
            AND sql LIKE '%UNIQUE%data%'
        """)
        
        if cursor.fetchone():
            print("   ⚠️  Constraint já existe, pulando...")
        else:
            # SQLite não suporta ADD CONSTRAINT, precisa recriar tabela
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS 
                idx_vendas_resumo_data_unique 
                ON read_vendas_resumo_diario(data)
            """)
            print("   ✅ UNIQUE constraint criada: read_vendas_resumo_diario(data)")
        
        print()
        
        # =====================================================================
        # 2. read_performance_parceiro: UNIQUE (funcionario_id, mes_referencia)
        # =====================================================================
        
        print("2️⃣ Adicionando UNIQUE constraint em read_performance_parceiro...")
        
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='index' AND tbl_name='read_performance_parceiro'
            AND sql LIKE '%UNIQUE%funcionario_id%'
        """)
        
        if cursor.fetchone():
            print("   ⚠️  Constraint já existe, pulando...")
        else:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS 
                idx_perf_func_mes_unique 
                ON read_performance_parceiro(funcionario_id, mes_referencia)
            """)
            print("   ✅ UNIQUE constraint criada: read_performance_parceiro(funcionario_id, mes_referencia)")
        
        print()
        
        # =====================================================================
        # 3. read_receita_mensal: UNIQUE (mes_referencia)
        # =====================================================================
        
        print("3️⃣ Adicionando UNIQUE constraint em read_receita_mensal...")
        
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='index' AND tbl_name='read_receita_mensal'
            AND sql LIKE '%UNIQUE%mes_referencia%'
        """)
        
        if cursor.fetchone():
            print("   ⚠️  Constraint já existe, pulando...")
        else:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS 
                idx_receita_mes_unique 
                ON read_receita_mensal(mes_referencia)
            """)
            print("   ✅ UNIQUE constraint criada: read_receita_mensal(mes_referencia)")
        
        print()
        
        # =====================================================================
        # COMMIT
        # =====================================================================
        
        conn.commit()
        
        print("=" * 70)
        print("✅ Migration 008 concluída com sucesso!")
        print()
        print("📋 Constraints de idempotência criadas:")
        print("   • read_vendas_resumo_diario: UNIQUE (data)")
        print("   • read_performance_parceiro: UNIQUE (funcionario_id, mes_referencia)")
        print("   • read_receita_mensal: UNIQUE (mes_referencia)")
        print()
        print("🎯 Handlers idempotentes agora podem usar UPSERT com segurança!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar migration: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


def rollback_migration():
    """Remove os constraints adicionados"""
    
    db_path = Path(__file__).parent.parent / "petshop.db"
    
    if not db_path.exists():
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        print("🔄 Revertendo Migration 008...")
        print()
        
        cursor.execute("DROP INDEX IF EXISTS idx_vendas_resumo_data_unique")
        print("   ✅ Removido: idx_vendas_resumo_data_unique")
        
        cursor.execute("DROP INDEX IF EXISTS idx_perf_func_mes_unique")
        print("   ✅ Removido: idx_perf_func_mes_unique")
        
        cursor.execute("DROP INDEX IF EXISTS idx_receita_mes_unique")
        print("   ✅ Removido: idx_receita_mes_unique")
        
        conn.commit()
        
        print()
        print("✅ Rollback concluído!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao reverter migration: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        aplicar_migration()
