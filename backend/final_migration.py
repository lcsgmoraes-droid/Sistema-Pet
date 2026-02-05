import subprocess
import sys
from sqlalchemy import text
from app.db import SessionLocal

print("===================================================")
print(" FASE 4.4 — EXECUÇÃO FINAL")
print(" MIGRATIONS + BACKFILL MULTI-TENANT")
print("===================================================\n")

# 1) Testar conexão
print("🔍 Testando conexão com o banco...")
try:
    db = SessionLocal()
    db.execute(text("SELECT 1"))
    db.close()
    print("✅ Conexão com banco OK\n")
except Exception as e:
    print("❌ Falha ao conectar no banco:", e)
    sys.exit(1)

# 2) Aplicar migrations
print("📦 Aplicando migrations (alembic upgrade head)...\n")
result = subprocess.run(
    ["alembic", "upgrade", "head"],
    capture_output=True,
    text=True,
)

print(result.stdout)
if result.returncode != 0:
    print("❌ ERRO AO APLICAR MIGRATIONS")
    print(result.stderr)
    sys.exit(1)

print("✅ Migrations aplicadas com sucesso\n")

# 3) Executar backfill
print("🧩 Executando backfill...\n")
db = SessionLocal()

try:
    tenant_id = db.execute(text("""
        INSERT INTO tenants (name)
        VALUES ('Empresa Padrão')
        RETURNING id
    """)).scalar()

    print(f"🏢 Tenant criado: {tenant_id}")

    users = db.execute(text("""
        SELECT id FROM users ORDER BY id
    """)).fetchall()

    if not users:
        print("⚠️ Nenhum usuário encontrado")
    else:
        for idx, row in enumerate(users):
            role = "owner" if idx == 0 else "staff"
            db.execute(
                text("""
                    UPDATE users
                    SET tenant_id = :tenant,
                        role = :role
                    WHERE id = :uid
                """),
                {"tenant": tenant_id, "role": role, "uid": row.id}
            )
            print(f"👤 User {row.id} -> tenant={tenant_id}, role={role}")

    db.commit()
    print("\n✅ BACKFILL EXECUTADO COM SUCESSO")

except Exception as e:
    db.rollback()
    print("❌ ERRO DURANTE BACKFILL:", e)
    sys.exit(1)

finally:
    db.close()

# 4) Validação final
print("\n🔎 Validação final:\n")
db = SessionLocal()
rows = db.execute(text("""
    SELECT id, tenant_id, role FROM users
""")).fetchall()
db.close()

for r in rows:
    print(f"User {r.id} | tenant={r.tenant_id} | role={r.role}")

print("\n===================================================")
print(" ✅ FASE 4.4 CONCLUÍDA COM SUCESSO")
print(" COPIE TODO ESTE OUTPUT E DEVOLVA AO ARQUITETO")
print("===================================================")
