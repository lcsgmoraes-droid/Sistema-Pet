"""
Teste direto de configuração WhatsApp no banco
"""
from app.db import get_session
from app.whatsapp.models import TenantWhatsAppConfig
import uuid

db = next(get_session())

# Dados
tenant_id = "7be8dad7-8956-4758-b7bc-855a5259fe2b"  # Empresa Padrão
openai_key = "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"

print(f"Criando config para tenant: {tenant_id}")

# Verificar se já existe
existing = db.query(TenantWhatsAppConfig).filter(
    TenantWhatsAppConfig.tenant_id == tenant_id
).first()

if existing:
    print(f"Configuração já existe! ID={existing.id}")
    print("Atualizando...")
    existing.openai_api_key = openai_key
    existing.model_preference = "gpt-4o-mini"
    existing.auto_response_enabled = True
    existing.bot_name = "Pet Shop Assistant"
    existing.greeting_message = "Olá! Como posso ajudar?"
    existing.tone = "friendly"
    db.commit()
    print("✅ Configuração atualizada!")
else:
    print("Criando nova configuração...")
    config = TenantWhatsAppConfig(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        provider="360dialog",
        api_key="SUA_CHAVE_360DIALOG_AQUI",
        phone_number="+5511999999999",
        webhook_secret="webhook_secret_123",
        openai_api_key=openai_key,
        model_preference="gpt-4o-mini",
        auto_response_enabled=True,
        bot_name="Pet Shop Assistant",
        greeting_message="Olá! Como posso ajudar?",
        tone="friendly"
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    print(f"✅ Configuração criada! ID={config.id}")

print("\n📊 Configuração WhatsApp + IA:")
print(f"   Provider: {config.provider if 'config' in locals() else existing.provider}")
print(f"   IA Model: {config.model_preference if 'config' in locals() else existing.model_preference}")
print(f"   Auto Response: {config.auto_response_enabled if 'config' in locals() else existing.auto_response_enabled}")
print(f"   Bot Name: {config.bot_name if 'config' in locals() else existing.bot_name}")
print("\n🎉 CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
