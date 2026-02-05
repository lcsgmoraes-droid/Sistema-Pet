"""
FASE 4.4 — PASSO 3
MIGRATIONS + BACKFILL CONTROLADO
"""
import subprocess
import sys
from sqlalchemy import text
from app.db import SessionLocal

print("===================================================")
print(" FASE 4.4 — PASSO 3 (POSTGRESQL)")
print(" MIGRATIONS + BACKFILL CONTROLADO")
print("===================================================\n")

# 1) Testar conexão com banco
print("🔍 Testando conexão com PostgreSQL...")
try:
    db = SessionLocal()
    db.execute(text("SELECT 1"))
    db.close()
    print("✅ PostgreSQL conectado com sucesso\n")
except Exception as e:
    print("❌ NÃO FOI POSSÍVEL CONECTAR AO POSTGRESQL")
    print("ERRO:", e)
    print("\n➡️ AÇÃO NECESSÁRIA:")
    print("- Suba os containers Docker (docker-compose up -d)")
    print("- Depois rode este bloco novamente")
    sys.exit(1)

# 2) Aplicar migrations
print("📦 Aplicando migrations Alembic (upgrade head)...\n")
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
print("🧩 Executando backfill controlado...\n")
db = SessionLocal()

try:
    # Criar tenant padrão
    tenant = db.execute(text("""
        INSERT INTO tenants (name)
        VALUES ('Empresa Padrão')
        RETURNING id
    """)).scalar()

    print(f"🏢 Tenant criado: {tenant}")

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
                {
                    "tenant": tenant,
                    "role": role,
                    "uid": row.id,
                }
            )
            print(f"👤 User {row.id} -> tenant={tenant}, role={role}")

    db.commit()
    print("\n✅ BACKFILL CONCLUÍDO COM SUCESSO")

except Exception as e:
    db.rollback()
    print("❌ ERRO DURANTE BACKFILL:", e)
    sys.exit(1)

finally:
    db.close()

print("\n===================================================")
print(" PASSO 3 FINALIZADO COM SUCESSO")
print(" COPIE TODO ESTE OUTPUT E DEVOLVA AO ARQUITETO")
print("===================================================")
