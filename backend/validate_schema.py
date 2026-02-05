from sqlalchemy import create_engine, text
from app.config import get_database_url

engine = create_engine(get_database_url())
conn = engine.connect()

print("=" * 60)
print("VERIFICAÇÃO DE SCHEMA - CONTAS_PAGAR")
print("=" * 60)

result = conn.execute(text("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'contas_pagar'
    AND column_name = 'tenant_id'
""")).fetchall()

if result:
    for row in result:
        print(f"✅ Coluna encontrada: {row[0]}")
        print(f"   Tipo: {row[1]}")
        print(f"   Nullable: {row[2]}")
        print(f"   Default: {row[3]}")
else:
    print("❌ Coluna tenant_id NÃO existe em contas_pagar")

print("\n" + "=" * 60)
print("VERIFICAÇÃO DE SCHEMA - CONTAS_RECEBER")
print("=" * 60)

result = conn.execute(text("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'contas_receber'
    AND column_name = 'tenant_id'
""")).fetchall()

if result:
    for row in result:
        print(f"✅ Coluna encontrada: {row[0]}")
        print(f"   Tipo: {row[1]}")
        print(f"   Nullable: {row[2]}")
        print(f"   Default: {row[3]}")
else:
    print("❌ Coluna tenant_id NÃO existe em contas_receber")

conn.close()
