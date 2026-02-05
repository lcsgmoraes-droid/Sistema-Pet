from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()
print("Verificando enums do PostgreSQL...\n")

# TipoCusto
result = db.execute(text("SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'tipocusto') ORDER BY enumsortorder"))
print("TipoCusto:")
for r in result:
    print(f"  - {r[0]}")

# EscopoRateio  
result = db.execute(text("SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'escoporateio') ORDER BY enumsortorder"))
print("\nEscopoRateio:")
for r in result:
    print(f"  - {r[0]}")

db.close()
