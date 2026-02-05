from sqlalchemy import text
from app.db import SessionLocal
from app.tenancy.context import set_current_tenant
from uuid import UUID

print("===================================================")
print(" TESTE DE BLINDAGEM MULTI-TENANT (SQLALCHEMY)")
print("===================================================\n")

db = SessionLocal()

print("1) TESTE SEM TENANT (DEVE FALHAR)")
try:
    db.execute(text("SELECT * FROM users"))
    print("❌ ERRO: Query executou sem tenant (NÃO ERA PRA ACONTECER)")
except Exception as e:
    print("✅ OK - Bloqueado corretamente")
    print("Erro:", e)

print("\n---------------------------------------------------")

print("2) TESTE COM TENANT (DEVE FUNCIONAR)")
try:
    # Use o tenant criado no backfill
    tenant_id = db.execute(text("SELECT id FROM tenants LIMIT 1")).scalar()
    set_current_tenant(tenant_id)

    result = db.execute(text("SELECT id, tenant_id FROM users")).fetchall()
    print("✅ OK - Query executou com tenant")
    for row in result:
        print(row)

except Exception as e:
    print("❌ ERRO inesperado:", e)

finally:
    db.close()

print("\n===================================================")
print(" FIM DO TESTE")
print(" COPIE TODO O OUTPUT E DEVOLVA AO ARQUITETO")
print("===================================================")
