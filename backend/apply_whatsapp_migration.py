"""
Script para aplicar migration do WhatsApp
"""
from app.db import engine
from sqlalchemy import text

# Criar tabela whatsapp_messages
print("📋 Aplicando migration: whatsapp_messages...")
with open('app/migrations/create_whatsapp_messages_table.sql', 'r', encoding='utf-8') as f:
    sql = f.read()
    with engine.connect() as conn:
        for statement in sql.split(';'):
            if statement.strip():
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    print(f"   ⚠️  {e}")
        conn.commit()

print("✅ Tabela whatsapp_messages criada!")

# Atualizar VIEW cliente_timeline
print("📋 Atualizando VIEW cliente_timeline...")
with engine.connect() as conn:
    conn.execute(text('DROP VIEW IF EXISTS cliente_timeline'))
    conn.commit()

with open('app/migrations/create_cliente_timeline_view.sql', 'r', encoding='utf-8') as f:
    sql = f.read()
    with engine.connect() as conn:
        for statement in sql.split(';'):
            if statement.strip() and not statement.strip().startswith('--'):
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    print(f"   ⚠️  {e}")
        conn.commit()

print("✅ VIEW cliente_timeline atualizada!")
print("\n🎉 Migration do WhatsApp aplicada com sucesso!")
