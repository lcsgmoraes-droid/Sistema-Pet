"""
Adiciona colunas de rateio à tabela notas_entrada
Para suportar rateio de custos entre loja física e online
"""
import psycopg2
import os

# Conexão com banco de dados
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/petshop_dev'
).replace('postgresql+psycopg2://', 'postgresql://')

def check_column_exists(cursor, column_name):
    """Verifica se uma coluna existe"""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='notas_entrada' 
        AND column_name=%s;
    """, (column_name,))
    return cursor.fetchone() is not None

def run_migration():
    """Adiciona colunas de rateio se não existirem"""
    
    print("🔧 Conectando ao banco de dados...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        colunas_adicionadas = []
        
        # 1. tipo_rateio
        if not check_column_exists(cursor, 'tipo_rateio'):
            print("📝 Adicionando coluna tipo_rateio...")
            cursor.execute("""
                ALTER TABLE notas_entrada 
                ADD COLUMN tipo_rateio VARCHAR(20) DEFAULT 'loja';
            """)
            cursor.execute("""
                COMMENT ON COLUMN notas_entrada.tipo_rateio IS 
                'Tipo de rateio: online, loja, parcial';
            """)
            colunas_adicionadas.append('tipo_rateio')
            print("   ✅ Coluna tipo_rateio adicionada")
        else:
            print("   ⏭️  Coluna tipo_rateio já existe")
        
        # 2. percentual_online
        if not check_column_exists(cursor, 'percentual_online'):
            print("📝 Adicionando coluna percentual_online...")
            cursor.execute("""
                ALTER TABLE notas_entrada 
                ADD COLUMN percentual_online FLOAT DEFAULT 0;
            """)
            colunas_adicionadas.append('percentual_online')
            print("   ✅ Coluna percentual_online adicionada")
        else:
            print("   ⏭️  Coluna percentual_online já existe")
        
        # 3. percentual_loja
        if not check_column_exists(cursor, 'percentual_loja'):
            print("📝 Adicionando coluna percentual_loja...")
            cursor.execute("""
                ALTER TABLE notas_entrada 
                ADD COLUMN percentual_loja FLOAT DEFAULT 100;
            """)
            colunas_adicionadas.append('percentual_loja')
            print("   ✅ Coluna percentual_loja adicionada")
        else:
            print("   ⏭️  Coluna percentual_loja já existe")
        
        # 4. valor_online
        if not check_column_exists(cursor, 'valor_online'):
            print("📝 Adicionando coluna valor_online...")
            cursor.execute("""
                ALTER TABLE notas_entrada 
                ADD COLUMN valor_online FLOAT DEFAULT 0;
            """)
            colunas_adicionadas.append('valor_online')
            print("   ✅ Coluna valor_online adicionada")
        else:
            print("   ⏭️  Coluna valor_online já existe")
        
        # 5. valor_loja
        if not check_column_exists(cursor, 'valor_loja'):
            print("📝 Adicionando coluna valor_loja...")
            cursor.execute("""
                ALTER TABLE notas_entrada 
                ADD COLUMN valor_loja FLOAT DEFAULT 0;
            """)
            colunas_adicionadas.append('valor_loja')
            print("   ✅ Coluna valor_loja adicionada")
        else:
            print("   ⏭️  Coluna valor_loja já existe")
        
        conn.commit()
        
        if colunas_adicionadas:
            print(f"\n✅ Migration concluída com sucesso!")
            print(f"📊 Colunas adicionadas: {', '.join(colunas_adicionadas)}")
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
