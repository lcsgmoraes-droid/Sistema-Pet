"""
Script de diagnóstico para erro 500 em POST /api/contas-bancarias

Execute com: python backend/scripts/diagnostico_conta_bancaria.py
"""
import sys
import os
from pathlib import Path

# Adicionar backend ao path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

print("🔍 DIAGNÓSTICO: Conta Bancária\n")
print("=" * 60)

# 1. Testar conexão DB primeiro (sem imports pesados)
print("\n1️⃣ Testando conexão com database...")
try:
    # Import minimal - só o que precisamos
    from sqlalchemy import create_engine, inspect, text, MetaData, Table, Column
    from sqlalchemy.orm import sessionmaker
    
    # Pegar database URL do ambiente ou default
    # IMPORTANTE: Docker Dev mapeia PostgreSQL na porta 5433 com credenciais simples
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5433/petshop_dev"
    )
    
    engine = create_engine(database_url)
    inspector = inspect(engine)
    tabelas = inspector.get_table_names()
    
    print(f"   ✅ Conexão OK - {len(tabelas)} tabelas encontradas")
    print(f"   📊 Database: {database_url.split('@')[-1]}")
    
except Exception as e:
    print(f"   ❌ Erro de conexão: {e}")
    print("\n   💡 Verifique:")
    print("      1. PostgreSQL está rodando?")
    print("      2. DATABASE_URL no .env está correto?")
    print("      3. Credenciais estão corretas?")
    sys.exit(1)

# 2. Verificar tabela contas_bancarias
print("\n2️⃣ Verificando tabela 'contas_bancarias'...")
if "contas_bancarias" in tabelas:
    print("   ✅ Tabela existe!")
    
    print("\n   Colunas:")
    colunas = inspector.get_columns("contas_bancarias")
    for col in colunas:
        nullable = "NULL" if col.get("nullable", False) else "NOT NULL"
        default = f"DEFAULT {col.get('default', 'N/A')}" if col.get('default') else ""
        print(f"      - {col['name']:<20} {col['type']!s:<20} {nullable:<10} {default}")
    
    print("\n   Índices:")
    indices = inspector.get_indexes("contas_bancarias")
    if indices:
        for idx in indices:
            print(f"      - {idx['name']}: {', '.join(idx['column_names'])}")
    else:
        print("      (nenhum)")
    
    print("\n   Foreign Keys:")
    fks = inspector.get_foreign_keys("contas_bancarias")
    for fk in fks:
        print(f"      - {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}")
        
else:
    print("   ❌ Tabela NÃO EXISTE!")
    print("\n   💡 Solução:")
    print("      cd backend")
    print("      alembic upgrade head")
    sys.exit(1)

# 3. Verificar usuário e tenant de teste
print("\n3️⃣ Verificando usuário e tenant de teste...")
try:
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Primeiro, descobrir quais colunas existem na tabela users
    users_columns = inspector.get_columns("users")
    users_col_names = [col['name'] for col in users_columns]
    
    # Verificar qual coluna usar para nome (username, email, name, etc.)
    name_col = None
    if 'username' in users_col_names:
        name_col = 'username'
    elif 'email' in users_col_names:
        name_col = 'email'
    elif 'name' in users_col_names:
        name_col = 'name'
    elif 'nome' in users_col_names:
        name_col = 'nome'
    else:
        name_col = users_col_names[1]  # Segunda coluna depois de id
    
    # Verificar users (via SQL raw)
    result = session.execute(text(f"SELECT id, {name_col}, tenant_id FROM users LIMIT 1"))
    user_row = result.first()
    
    if not user_row:
        print("   ❌ Nenhum usuário encontrado no banco")
        print("   💡 Crie um usuário antes de continuar")
        session.close()
        sys.exit(1)
    
    user_id, user_name, tenant_id = user_row
    print(f"   ✅ Usuário encontrado: {user_name} (ID: {user_id})")
    
    # Verificar tenant (detectar nome da coluna automaticamente)
    tenants_columns = inspector.get_columns("tenants")
    tenants_col_names = [col['name'] for col in tenants_columns]
    
    tenant_name_col = None
    if 'nome' in tenants_col_names:
        tenant_name_col = 'nome'
    elif 'name' in tenants_col_names:
        tenant_name_col = 'name'
    else:
        tenant_name_col = tenants_col_names[1]  # Segunda coluna
    
    result = session.execute(
        text(f"SELECT id, {tenant_name_col} FROM tenants WHERE id = :tenant_id"),
        {"tenant_id": str(tenant_id)}
    )
    tenant_row = result.first()
    
    if not tenant_row:
        print(f"   ❌ Tenant do usuário não encontrado (tenant_id: {tenant_id})")
        session.close()
        sys.exit(1)
    
    tenant_id_db, tenant_nome = tenant_row
    print(f"   ✅ Tenant encontrado: {tenant_nome} (ID: {tenant_id_db})")
    
except Exception as e:
    print(f"   ❌ Erro ao verificar user/tenant: {e}")
    import traceback
    traceback.print_exc()
    if 'session' in locals():
        session.close()
    sys.exit(1)

# 4. Simular criação de conta
print("\n4️⃣ Simulando criação de conta bancária...")
try:
    from decimal import Decimal
    from datetime import datetime
    import uuid
    
    # Dados do teste (igual ao que o frontend envia)
    conta_data = {
        "nome": "Teste Diagnóstico",
        "tipo": "caixa",
        "banco": None,
        "saldo_inicial": Decimal("0.00"),
        "saldo_atual": Decimal("0.00"),
        "cor": "#16a34a",
        "icone": None,
        "ativa": True,
        "user_id": user_id,
        "tenant_id": str(tenant_id),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    print(f"   Dados da conta:")
    for key, value in conta_data.items():
        print(f"      {key}: {value!r} ({type(value).__name__})")
    
    # Criar conta via INSERT
    print("\n   Criando conta via SQL...")
    
    insert_sql = text("""
        INSERT INTO contas_bancarias 
        (nome, tipo, banco, saldo_inicial, saldo_atual, cor, icone, ativa, user_id, tenant_id, created_at, updated_at)
        VALUES 
        (:nome, :tipo, :banco, :saldo_inicial, :saldo_atual, :cor, :icone, :ativa, :user_id, :tenant_id, :created_at, :updated_at)
        RETURNING id
    """)
    
    result = session.execute(insert_sql, conta_data)
    conta_id = result.scalar()
    session.commit()
    
    print(f"   ✅ Conta criada com sucesso! ID: {conta_id}")
    
    # Deletar o teste (rollback manual)
    session.execute(text("DELETE FROM contas_bancarias WHERE id = :id"), {"id": conta_id})
    session.commit()
    print("   🔄 Conta de teste removida (cleanup)")

except Exception as e:
    print(f"   ❌ ERRO ao criar conta: {e}")
    print(f"\n   Tipo do erro: {type(e).__name__}")
    print("\n   Traceback completo:")
    import traceback
    traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 CAUSA RAIZ ENCONTRADA!")
    print("=" * 60)
    
    # Análise do erro
    error_str = str(e).lower()
    
    if "foreign key" in error_str:
        print("\n❌ PROBLEMA: Violação de chave estrangeira")
        print("   • user_id ou tenant_id não existe no banco")
        print("   • Verifique se o usuário está logado corretamente")
        
    elif "not null" in error_str or "null value" in error_str:
        print("\n❌ PROBLEMA: Campo obrigatório ausente")
        print("   • Algum campo NOT NULL está recebendo NULL")
        print("   • Verifique os dados enviados do frontend")
        
    elif "unique constraint" in error_str or "duplicate" in error_str:
        print("\n❌ PROBLEMA: Registro duplicado")
        print("   • Já existe uma conta com esse nome")
        
    elif "does not exist" in error_str:
        print("\n❌ PROBLEMA: Coluna ou tabela ausente")
        print("   • Execute: alembic upgrade head")
        
    else:
        print("\n❓ PROBLEMA DESCONHECIDO")
        print("   • Veja o traceback acima para mais detalhes")
    
    if 'session' in locals():
        session.rollback()
        session.close()
    sys.exit(1)

# 5. Verificar contas existentes
print("\n5️⃣ Contas bancárias existentes...")
try:
    result = session.execute(
        text("""
            SELECT id, nome, tipo, saldo_atual 
            FROM contas_bancarias 
            WHERE tenant_id = :tenant_id
            ORDER BY created_at DESC
            LIMIT 10
        """),
        {"tenant_id": str(tenant_id)}
    )
    contas = result.fetchall()
    
    if contas:
        print(f"   📊 {len(contas)} conta(s) encontrada(s):")
        for conta in contas:
            conta_id, nome, tipo, saldo = conta
            print(f"      - {nome} ({tipo}) - Saldo: R$ {float(saldo):.2f}")
    else:
        print("   📭 Nenhuma conta cadastrada ainda")

except Exception as e:
    print(f"   ⚠️ Erro ao listar contas: {e}")

# Fechar sessão
if 'session' in locals():
    session.close()

# Resultado final
print("\n" + "=" * 60)
print("✅ DIAGNÓSTICO CONCLUÍDO!")
print("=" * 60)
print("\nTodos os testes passaram! 🎉")
print("\nSe o erro 500 persiste:")
print("1. Verifique os logs do backend (terminal onde uvicorn está rodando)")
print("2. Procure por 'ERROR' ou 'Traceback' nos logs")
print("3. Execute este script novamente para validar")
print("\n💡 Dica: Coloque ENVIRONMENT=development no .env para ver erros completos")
