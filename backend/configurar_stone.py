"""
Configuração automática da Stone no banco de dados
Usa as credenciais do .env para configurar o primeiro tenant
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import SessionLocal
from app.stone_models import StoneConfig
from app.config import STONE_CLIENT_ID, STONE_CLIENT_SECRET, STONE_MERCHANT_ID, STONE_SANDBOX, STONE_WEBHOOK_SECRET
from sqlalchemy import text


def configurar_stone_automatico():
    """Configura Stone para o primeiro tenant encontrado"""
    
    print("="*60)
    print("🔧 CONFIGURAÇÃO AUTOMÁTICA - STONE PAGAMENTOS")
    print("="*60)
    print()
    
    # Verifica se credenciais estão configuradas no .env
    if not STONE_CLIENT_ID or STONE_CLIENT_ID == "":
        print("❌ ERRO: STONE_CLIENT_ID não configurado no .env")
        print()
        print("Configure as variáveis no arquivo .env:")
        print("STONE_CLIENT_ID=sk_...")
        print("STONE_CLIENT_SECRET=sk_...")
        print("STONE_MERCHANT_ID=...")
        return False
    
    print("✅ Credenciais encontradas no .env:")
    print(f"   Client ID: {STONE_CLIENT_ID[:20]}...")
    print(f"   Sandbox: {STONE_SANDBOX}")
    print()
    
    db = SessionLocal()
    
    try:
        # Busca primeiro tenant
        result = db.execute(text("SELECT id FROM tenants LIMIT 1"))
        tenant_row = result.fetchone()
        
        if not tenant_row:
            print("❌ Nenhum tenant encontrado no banco!")
            print("   Crie um tenant primeiro via interface ou SQL")
            return False
        
        tenant_id = tenant_row[0]
        print(f"✅ Tenant encontrado: {tenant_id}")
        print()
        
        # Busca primeiro usuário do tenant
        result = db.execute(text(f"SELECT id FROM users WHERE tenant_id = {tenant_id} LIMIT 1"))
        user_row = result.fetchone()
        
        if not user_row:
            print("❌ Nenhum usuário encontrado para o tenant!")
            return False
        
        user_id = user_row[0]
        print(f"✅ Usuário encontrado: {user_id}")
        print()
        
        # Verifica se já existe configuração Stone
        existing = db.query(StoneConfig).filter(
            StoneConfig.tenant_id == tenant_id
        ).first()
        
        if existing:
            print("⚠️  Configuração Stone já existe!")
            print(f"   ID: {existing.id}")
            print(f"   Criada em: {existing.created_at}")
            print()
            
            resposta = input("Deseja atualizar? (s/N): ").strip().lower()
            if resposta != 's':
                print("❌ Operação cancelada")
                return False
            
            # Atualiza configuração existente
            existing.client_id = STONE_CLIENT_ID
            existing.client_secret = STONE_CLIENT_SECRET
            existing.merchant_id = STONE_MERCHANT_ID or existing.merchant_id
            existing.sandbox = STONE_SANDBOX
            existing.webhook_secret = STONE_WEBHOOK_SECRET or existing.webhook_secret
            existing.webhook_url = f"https://seu-dominio.com/api/stone/webhook"
            
            db.commit()
            print("✅ Configuração Stone atualizada com sucesso!")
            
        else:
            # Cria nova configuração
            config = StoneConfig(
                tenant_id=tenant_id,
                user_id=user_id,
                client_id=STONE_CLIENT_ID,
                client_secret=STONE_CLIENT_SECRET,
                merchant_id=STONE_MERCHANT_ID or "configurar_depois",
                webhook_secret=STONE_WEBHOOK_SECRET,
                sandbox=STONE_SANDBOX,
                enable_pix=True,
                enable_credit_card=True,
                enable_debit_card=False,
                max_installments=12,
                webhook_url=f"https://seu-dominio.com/api/stone/webhook",
                webhook_enabled=True,
                active=True
            )
            
            db.add(config)
            db.commit()
            db.refresh(config)
            
            print("✅ Configuração Stone criada com sucesso!")
            print(f"   ID: {config.id}")
        
        print()
        print("="*60)
        print("📊 CONFIGURAÇÃO ATUAL:")
        print("="*60)
        print(f"Tenant ID: {tenant_id}")
        print(f"Client ID: {STONE_CLIENT_ID[:20]}...")
        print(f"Merchant ID: {STONE_MERCHANT_ID or 'NÃO CONFIGURADO'}")
        print(f"Ambiente: {'SANDBOX (Testes)' if STONE_SANDBOX else 'PRODUÇÃO'}")
        print(f"PIX: Ativado")
        print(f"Cartão Crédito: Ativado")
        print(f"Cartão Débito: Desativado")
        print(f"Parcelas: Até 12x")
        print()
        
        if not STONE_MERCHANT_ID:
            print("⚠️  ATENÇÃO: STONE_MERCHANT_ID não configurado no .env")
            print("   Você precisa do Merchant ID para processar pagamentos")
            print("   Adicione no .env: STONE_MERCHANT_ID=seu_merchant_id")
            print()
        
        print("="*60)
        print("✅ CONFIGURAÇÃO CONCLUÍDA!")
        print("="*60)
        print()
        print("Próximos passos:")
        print("1. Configure o STONE_MERCHANT_ID no .env (se ainda não tiver)")
        print("2. Configure o webhook no dashboard Stone:")
        print(f"   URL: https://seu-dominio.com/api/stone/webhook")
        print("3. Teste a conexão: python teste_stone_api.py")
        print("4. Teste criar um pagamento via API")
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
    configurar_stone_automatico()
    print()
