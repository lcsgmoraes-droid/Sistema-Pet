"""
Configuração Stone usando banco de dados STAGING
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório backend ao path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Configura para usar o banco staging
os.environ['POSTGRES_USER'] = 'petshop_staging'
os.environ['POSTGRES_PASSWORD'] = 'staging_pass_2026_local'
os.environ['POSTGRES_DB'] = 'petshop_staging_db'
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['DATABASE_URL'] = 'postgresql://petshop_staging:staging_pass_2026_local@localhost:5432/petshop_staging_db'

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Stone configs
STONE_CLIENT_ID = "sk_83973c1ff4674497bade8bd2bf8856da"
STONE_CLIENT_SECRET = "sk_83973c1ff4674497bade8bd2bf8856da"
STONE_MERCHANT_ID = "128845743"
STONE_SANDBOX = True


def configurar_stone_staging():
    """Configura Stone no banco staging"""
    
    print("="*60)
    print("🔧 CONFIGURAÇÃO STONE - BANCO STAGING")
    print("="*60)
    print()
    
    # Conecta no banco staging
    DATABASE_URL = "postgresql://petshop_staging:staging_pass_2026_local@localhost:5432/petshop_staging_db"
    
    print(f"📦 Conectando no banco staging...")
    print(f"   URL: {DATABASE_URL}")
    print()
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Testa conexão
        result = db.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✅ Conectado ao PostgreSQL!")
        print(f"   Versão: {version[:50]}...")
        print()
        
        # Busca primeiro tenant
        result = db.execute(text("SELECT id, nome FROM tenants LIMIT 1"))
        tenant_row = result.fetchone()
        
        if not tenant_row:
            print("❌ Nenhum tenant encontrado!")
            print("   Crie um tenant primeiro")
            return False
        
        tenant_id = tenant_row[0]
        tenant_nome = tenant_row[1]
        print(f"✅ Tenant encontrado:")
        print(f"   ID: {tenant_id}")
        print(f"   Nome: {tenant_nome}")
        print()
        
        # Busca primeiro usuário
        result = db.execute(text(f"SELECT id, username FROM users WHERE tenant_id = {tenant_id} LIMIT 1"))
        user_row = result.fetchone()
        
        if not user_row:
            print("❌ Nenhum usuário encontrado!")
            return False
        
        user_id = user_row[0]
        user_name = user_row[1]
        print(f"✅ Usuário encontrado:")
        print(f"   ID: {user_id}")
        print(f"   Username: {user_name}")
        print()
        
        # Verifica se tabela stone_configs existe
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'stone_configs'
            )
        """))
        
        table_exists = result.fetchone()[0]
        
        if not table_exists:
            print("⚠️  Tabela stone_configs não existe!")
            print("   Criando tabela...")
            
            # Cria tabela
            db.execute(text("""
                CREATE TABLE stone_configs (
                    id SERIAL PRIMARY KEY,
                    tenant_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    client_id VARCHAR(200) NOT NULL,
                    client_secret VARCHAR(200) NOT NULL,
                    merchant_id VARCHAR(200) NOT NULL,
                    webhook_secret VARCHAR(200),
                    sandbox BOOLEAN DEFAULT true,
                    enable_pix BOOLEAN DEFAULT true,
                    enable_credit_card BOOLEAN DEFAULT true,
                    enable_debit_card BOOLEAN DEFAULT false,
                    max_installments INTEGER DEFAULT 12,
                    webhook_url VARCHAR(500),
                    webhook_enabled BOOLEAN DEFAULT true,
                    active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            db.commit()
            print("✅ Tabela criada!")
            print()
        
        # Verifica se já existe config
        result = db.execute(text(f"SELECT id FROM stone_configs WHERE tenant_id = {tenant_id}"))
        existing = result.fetchone()
        
        if existing:
            print("⚠️  Configuração já existe!")
            print(f"   ID: {existing[0]}")
            print()
            
            resposta = input("Deseja atualizar? (s/N): ").strip().lower()
            if resposta != 's':
                print("❌ Cancelado")
                return False
            
            # Atualiza
            db.execute(text(f"""
                UPDATE stone_configs SET
                    client_id = '{STONE_CLIENT_ID}',
                    client_secret = '{STONE_CLIENT_SECRET}',
                    merchant_id = '{STONE_MERCHANT_ID}',
                    sandbox = {STONE_SANDBOX},
                    updated_at = NOW()
                WHERE tenant_id = {tenant_id}
            """))
            db.commit()
            print("✅ Atualizado!")
        else:
            # Insere novo
            db.execute(text(f"""
                INSERT INTO stone_configs (
                    tenant_id, user_id, client_id, client_secret, merchant_id,
                    sandbox, enable_pix, enable_credit_card, enable_debit_card,
                    max_installments, webhook_url, webhook_enabled, active
                ) VALUES (
                    {tenant_id}, {user_id}, 
                    '{STONE_CLIENT_ID}', '{STONE_CLIENT_SECRET}', '{STONE_MERCHANT_ID}',
                    {STONE_SANDBOX}, true, true, false,
                    12, 'https://seu-dominio.com/api/stone/webhook', true, true
                )
            """))
            db.commit()
            print("✅ Configuração criada!")
        
        print()
        print("="*60)
        print("✅ SUCESSO!")
        print("="*60)
        print()
        print(f"Tenant: {tenant_nome} (ID: {tenant_id})")
        print(f"Client ID: {STONE_CLIENT_ID[:20]}...")
        print(f"Merchant ID: {STONE_MERCHANT_ID}")
        print(f"Ambiente: {'SANDBOX (Testes)' if STONE_SANDBOX else 'PRODUÇÃO'}")
        print()
        print("Próximos passos:")
        print("1. Teste a API: python backend/teste_stone_api.py")
        print("2. Inicie o backend: python backend/run_server.py")
        print("3. Teste criar pagamento via POST /api/stone/payments/pix")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    print()
    configurar_stone_staging()
    print()
