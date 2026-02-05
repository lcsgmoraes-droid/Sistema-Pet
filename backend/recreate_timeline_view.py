"""
Script para recriar a VIEW cliente_timeline
"""
from app.db import engine
from sqlalchemy import text

print("📋 Verificando VIEW cliente_timeline...")

# Verificar se VIEW existe
with engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='view' AND name='cliente_timeline'")).fetchall()
    existe = len(result) > 0
    print(f"   VIEW existe: {existe}")

# Dropar VIEW se existir
print("\n📋 Recriando VIEW cliente_timeline...")
with engine.connect() as conn:
    try:
        conn.execute(text('DROP VIEW IF EXISTS cliente_timeline'))
        conn.commit()
        print("   ✅ VIEW antiga removida")
    except Exception as e:
        print(f"   ⚠️  Erro ao dropar: {e}")

# Criar VIEW
print("\n📋 Criando VIEW cliente_timeline...")
with open('app/migrations/create_cliente_timeline_view.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()
    
    # Remover comentários e linhas vazias
    lines = []
    for line in sql_content.split('\n'):
        line = line.strip()
        if line and not line.startswith('--') and not line.startswith('COMMENT'):
            lines.append(line)
    
    sql = ' '.join(lines)
    
    # Dividir por ponto-e-vírgula para executar comandos separados
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    
    with engine.connect() as conn:
        for statement in statements:
            if 'CREATE VIEW' in statement or 'CREATE INDEX' in statement:
                try:
                    conn.execute(text(statement))
                    conn.commit()
                    if 'CREATE VIEW' in statement:
                        print("   ✅ VIEW criada!")
                    else:
                        print("   ✅ Índice criado")
                except Exception as e:
                    print(f"   ⚠️  {e}")

# Verificar novamente
print("\n📋 Verificando resultado...")
with engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='view' AND name='cliente_timeline'")).fetchall()
    existe = len(result) > 0
    
    if existe:
        print("   ✅ VIEW cliente_timeline criada com sucesso!")
        
        # Testar query
        try:
            result = conn.execute(text("SELECT COUNT(*) as total FROM cliente_timeline")).fetchone()
            print(f"   📊 Total de eventos na timeline: {result[0]}")
        except Exception as e:
            print(f"   ⚠️  Erro ao testar VIEW: {e}")
    else:
        print("   ❌ VIEW não foi criada!")

print("\n🎉 Processo concluído!")
