"""
Adiciona colunas de rateio para contas_pagar e notas_entrada_itens
"""
import psycopg2
import os

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/petshop_dev'
).replace('postgresql+psycopg2://', 'postgresql://')

def check_column_exists(cursor, table_name, column_name):
    """Verifica se uma coluna existe"""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name=%s 
        AND column_name=%s;
    """, (table_name, column_name))
    return cursor.fetchone() is not None

def run_migration():
    """Adiciona colunas de rateio"""
    
    print("🔧 Conectando ao banco de dados...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        colunas_adicionadas = []
        
        # ===== CONTAS_PAGAR =====
        print("\n📋 Processando tabela contas_pagar...")
        
        if not check_column_exists(cursor, 'contas_pagar', 'percentual_online'):
            print("  📝 Adicionando percentual_online...")
            cursor.execute("""
                ALTER TABLE contas_pagar 
                ADD COLUMN percentual_online FLOAT DEFAULT 0;
            """)
            colunas_adicionadas.append('contas_pagar.percentual_online')
            print("     ✅ Coluna adicionada")
        else:
            print("  ⏭️  percentual_online já existe")
        
        if not check_column_exists(cursor, 'contas_pagar', 'percentual_loja'):
            print("  📝 Adicionando percentual_loja...")
            cursor.execute("""
                ALTER TABLE contas_pagar 
                ADD COLUMN percentual_loja FLOAT DEFAULT 100;
            """)
            colunas_adicionadas.append('contas_pagar.percentual_loja')
            print("     ✅ Coluna adicionada")
        else:
            print("  ⏭️  percentual_loja já existe")
        
        # ===== NOTAS_ENTRADA_ITENS =====
        print("\n📋 Processando tabela notas_entrada_itens...")
        
        if not check_column_exists(cursor, 'notas_entrada_itens', 'quantidade_online'):
            print("  📝 Adicionando quantidade_online...")
            cursor.execute("""
                ALTER TABLE notas_entrada_itens 
                ADD COLUMN quantidade_online FLOAT DEFAULT 0;
            """)
            colunas_adicionadas.append('notas_entrada_itens.quantidade_online')
            print("     ✅ Coluna adicionada")
        else:
            print("  ⏭️  quantidade_online já existe")
        
        if not check_column_exists(cursor, 'notas_entrada_itens', 'valor_online'):
            print("  📝 Adicionando valor_online...")
            cursor.execute("""
                ALTER TABLE notas_entrada_itens 
                ADD COLUMN valor_online FLOAT DEFAULT 0;
            """)
            colunas_adicionadas.append('notas_entrada_itens.valor_online')
            print("     ✅ Coluna adicionada")
        else:
            print("  ⏭️  valor_online já existe")
        
        conn.commit()
        
        if colunas_adicionadas:
            print(f"\n✅ Migration concluída com sucesso!")
            print(f"📊 Colunas adicionadas:")
            for col in colunas_adicionadas:
                print(f"   - {col}")
        else:
            print("\n✅ Todas as colunas já existem - nada a fazer!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro na migration: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
