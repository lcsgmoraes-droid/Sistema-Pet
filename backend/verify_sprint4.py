from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()

result = db.execute(text("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name LIKE 'whatsapp%' 
    ORDER BY table_name
"""))

print("\n=== Tabelas WhatsApp ===")
for row in result:
    print(f"✓ {row[0]}")

db.close()
print("\nChecando se Sprint 4 foi criada...")

# Verificar tabelas específicas do Sprint 4
sprint4_tables = ['whatsapp_agents', 'whatsapp_handoffs', 'whatsapp_internal_notes']

for table in sprint4_tables:
    result = db.execute(text(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = '{table}'
        )
    """))
    exists = result.scalar()
    status = "✅" if exists else "❌"
    print(f"{status} {table}")

db = SessionLocal()
result = db.execute(text("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name IN ('whatsapp_agents', 'whatsapp_handoffs', 'whatsapp_internal_notes')
"""))

print("\n=== Tabelas Sprint 4 ===")
count = 0
for row in result:
    print(f"✅ {row[0]}")
    count += 1

if count == 3:
    print("\n🎉 SPRINT 4 - Todas as tabelas criadas!")
else:
    print(f"\n⚠️ Faltam {3 - count} tabelas")

db.close()
