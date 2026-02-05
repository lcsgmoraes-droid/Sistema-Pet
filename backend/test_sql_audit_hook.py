"""
🧪 Teste de Validação do SQL Audit Hook
========================================

Valida que o hook detecta RAW SQL fora do helper e NÃO loga quando vem do helper.
"""

import os
import sys

# Configurar ambiente
os.environ['DATABASE_URL'] = "postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db"
sys.path.insert(0, os.path.abspath('.'))

print("=" * 80)
print("TESTE SQL AUDIT HOOK")
print("=" * 80)

# Importar e ativar hook
from app.db.sql_audit import enable_sql_audit, get_audit_stats

print("\n[1] Ativando SQL Audit...")
enable_sql_audit()
stats = get_audit_stats()
print(f"✅ Status: {stats['status']}")
print(f"✅ Listener: {'Ativo' if stats['listener_registered'] else 'Inativo'}")

# Criar sessão de banco
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.environ['DATABASE_URL'], echo=False)
Session = sessionmaker(bind=engine)
session = Session()

print("\n" + "=" * 80)
print("TESTE 1: RAW SQL DIRETO (deve logar ALERTA)")
print("=" * 80)
print("Executando: SELECT com COALESCE (indicador de RAW SQL)...\n")

try:
    result = session.execute(text("""
        SELECT 
            1 as test_id,
            'Test' as test_name,
            COALESCE(NULL, 'default') as test_value
    """))
    row = result.fetchone()
    print(f"✅ Query executada com sucesso")
    print(f"   Resultado: {dict(row._mapping)}")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n(Aguarde log de auditoria acima ☝️)")

print("\n" + "=" * 80)
print("TESTE 2: RAW SQL COM HELPER (NAO deve logar OK)")
print("=" * 80)
print("Executando: SELECT via execute_tenant_safe...\n")

try:
    from app.utils.tenant_safe_sql import execute_tenant_safe
    from app.tenancy.context import set_current_tenant
    from uuid import uuid4
    
    # Configurar tenant (necessário para helper)
    tenant_id = uuid4()
    set_current_tenant(tenant_id)
    print(f"📝 Tenant configurado: {tenant_id}")
    
    # Executar com helper (require_tenant=False para query de teste)
    result = execute_tenant_safe(session, """
        SELECT 
            2 as test_id,
            'Test Safe' as test_name
        WHERE {tenant_filter}
    """, {}, require_tenant=False)
    
    row = result.fetchone()
    print(f"✅ Query executada com sucesso (via helper)")
    print(f"   Resultado: {dict(row._mapping)}")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()

print("\n(NÃO deve ter log de auditoria acima)")

print("\n" + "=" * 80)
print("TESTE 3: Query ORM (NAO deve logar OK)")
print("=" * 80)
print("Executando: SELECT simples sem indicadores de RAW SQL...\n")

try:
    result = session.execute(text("SELECT 3 as simple_id"))
    row = result.fetchone()
    print(f"✅ Query executada com sucesso")
    print(f"   Resultado: {dict(row._mapping)}")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n(NÃO deve ter log de auditoria - query muito simples)")

# Cleanup
session.close()

print("\n" + "=" * 80)
print("RESUMO")
print("=" * 80)
print("[OK] Teste 1: RAW SQL direto -> DEVE ter logado ALERTA")
print("[OK] Teste 2: RAW SQL via helper -> NAO deve ter logado")
print("[OK] Teste 3: Query simples -> NAO deve ter logado")
print("\nVERIFIQUE os logs acima para confirmar comportamento")
print("=" * 80)
