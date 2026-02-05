"""
Script para testar o sistema WhatsApp
"""
from app.db import engine, get_session
from app.models import WhatsAppMessage
from datetime import datetime
from sqlalchemy import text

print("📋 Testando sistema WhatsApp CRM...")

# Verificar se tabela existe
print("\n1️⃣ Verificando tabela whatsapp_messages...")
with engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='whatsapp_messages'")).fetchall()
    if result:
        print("   ✅ Tabela existe")
        
        # Contar mensagens
        count = conn.execute(text("SELECT COUNT(*) FROM whatsapp_messages")).fetchone()[0]
        print(f"   📊 Total de mensagens: {count}")
    else:
        print("   ❌ Tabela não existe!")

# Verificar VIEW
print("\n2️⃣ Verificando VIEW cliente_timeline...")
with engine.connect() as conn:
    # Contar eventos WhatsApp na timeline
    count = conn.execute(text("SELECT COUNT(*) FROM cliente_timeline WHERE tipo_evento='whatsapp'")).fetchone()[0]
    print(f"   📊 Eventos WhatsApp na timeline: {count}")

# Verificar estrutura da tabela
print("\n3️⃣ Estrutura da tabela:")
with engine.connect() as conn:
    result = conn.execute(text("PRAGMA table_info(whatsapp_messages)")).fetchall()
    for row in result:
        print(f"   - {row[1]} ({row[2]})")

print("\n✅ Testes concluídos!")
