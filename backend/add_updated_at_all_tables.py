"""
Script para adicionar coluna updated_at em todas as tabelas que precisam
"""
from sqlalchemy import create_engine, text
from app.config import get_database_url, DATABASE_TYPE

if DATABASE_TYPE != "postgresql":
    print(f"ℹ Database type is {DATABASE_TYPE}, not PostgreSQL.")
    print("ℹ Este script é específico para PostgreSQL.")
    exit(0)

engine = create_engine(get_database_url())

# Lista de tabelas que precisam da coluna updated_at
TABELAS = [
    'estoque_movimentacoes',
    'recebimentos',
    'pagamentos',
    'lancamentos_previstos',
    'contas_receber',
    'contas_pagar',
]

print("🔧 Adicionando coluna updated_at em tabelas do sistema...\n")

with engine.begin() as conn:
    tabelas_atualizadas = 0
    tabelas_ja_existentes = 0
    
    for tabela in TABELAS:
        try:
            # Verifica se a tabela existe
            result = conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{tabela}'
                );
            """))
            
            if not result.scalar():
                print(f"⏭️ Tabela '{tabela}' não existe, pulando...")
                continue
            
            # Verifica se a coluna já existe
            result = conn.execute(text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='{tabela}' 
                AND column_name='updated_at';
            """))
            
            if result.scalar():
                print(f"✅ {tabela}: updated_at já existe")
                tabelas_ja_existentes += 1
            else:
                # Adiciona a coluna
                conn.execute(text(f"""
                    ALTER TABLE {tabela} 
                    ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                """))
                
                # Preenche com created_at para registros existentes
                conn.execute(text(f"""
                    UPDATE {tabela} 
                    SET updated_at = created_at 
                    WHERE updated_at IS NULL;
                """))
                
                print(f"✅ {tabela}: updated_at ADICIONADA e inicializada")
                tabelas_atualizadas += 1
                
        except Exception as e:
            print(f"❌ Erro ao processar {tabela}: {str(e)}")
            continue

print("\n" + "="*60)
print("🚀 MIGRAÇÃO COMPLETA!")
print(f"📊 Tabelas processadas: {len(TABELAS)}")
print(f"✅ Tabelas atualizadas: {tabelas_atualizadas}")
print(f"ℹ️  Tabelas já tinham updated_at: {tabelas_ja_existentes}")
print("="*60)
print("\n✅ Reinicie o backend para testar as vendas.")
