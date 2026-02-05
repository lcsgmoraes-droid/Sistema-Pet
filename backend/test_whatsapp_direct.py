"""
Test script to debug WhatsApp config creation
"""
import sys
sys.path.append(".")

from app.db import SessionLocal
from app.models import User, Tenant
from app.whatsapp.models import TenantWhatsAppConfig
import uuid

db = SessionLocal()

try:
    # Buscar tenant
    tenant = db.query(Tenant).first()
    print(f"✅ Tenant encontrado: {tenant.id} - {tenant.name}")
    
    # Tentar criar config
    config = TenantWhatsAppConfig(
        tenant_id=tenant.id,
        provider="360dialog",
        openai_api_key="sk-proj-test",
        model_preference="gpt-4o-mini",
        auto_response_enabled=True,
        bot_name="Assistente Pet Shop",
        greeting_message="Ola! Sou o assistente virtual. Como posso ajudar?",
        tone="friendly"
    )
    
    print(f"✅ Config criada na memória")
    print(f"   tenant_id: {config.tenant_id}")
    print(f"   provider: {config.provider}")
    
    # Tentar salvar
    db.add(config)
    db.commit()
    db.refresh(config)
    
    print(f"✅ Config salva no banco!")
    print(f"   ID: {config.id}")
    
    # Buscar de volta
    saved = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == tenant.id
    ).first()
    
    print(f"✅ Config recuperada: {saved.id}")
    
except Exception as e:
    print(f"❌ ERRO: {type(e).__name__}")
    print(f"   Mensagem: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
