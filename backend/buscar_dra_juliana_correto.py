"""
Script para verificar a Dra Juliana Duarte (ID 14) no BANCO CORRETO
Agora buscando na tabela CLIENTES com tipo_cadastro = veterinario
"""
import sqlite3
import os

# Caminho do banco CORRETO (usado pelas rotas)
db_path = os.path.join(os.path.dirname(__file__), "petshop.db")
print(f"📂 Banco de dados: {db_path}")
print(f"✅ Existe: {os.path.exists(db_path)}\n")

if not os.path.exists(db_path):
    print("❌ Banco 'petshop.db' não encontrado. Abortando...")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("="*80)
print("VERIFICANDO DRA JULIANA DUARTE (ID 14) NO BANCO CORRETO")
print("="*80)

# 1. Listar todas as tabelas
print("\n📋 TABELAS NO BANCO:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
for t in tables:
    print(f"   - {t['name']}")

# 2. Verificar se existe na tabela clientes com ID 14
print("\n\n🔍 BUSCANDO ID 14 NA TABELA 'clientes' (tipo_cadastro = veterinario/funcionario):")
try:
    cursor.execute("""
        SELECT id, nome, tipo_cadastro, tipo_pessoa, email, crmv, ativo
        FROM clientes 
        WHERE id = 14
    """)
    result = cursor.fetchone()
    
    if result:
        print(f"   ✅ ENCONTRADO!")
        print(f"   ID: {result['id']}")
        print(f"   Nome: {result['nome']}")
        print(f"   Tipo Cadastro: {result['tipo_cadastro']}")
        print(f"   Tipo Pessoa: {result['tipo_pessoa']}")
        print(f"   Email: {result['email']}")
        print(f"   CRMV: {result['crmv']}")
        print(f"   Ativo: {result['ativo']}")
    else:
        print("   ❌ ID 14 NÃO ENCONTRADO")
except Exception as e:
    print(f"   ❌ ERRO: {e}")

# 3. Buscar pela pessoa "Juliana" na tabela clientes
print("\n\n🔍 BUSCANDO 'JULIANA' NA TABELA 'clientes':")
try:
    cursor.execute("""
        SELECT id, nome, tipo_cadastro, tipo_pessoa, email, crmv, ativo
        FROM clientes 
        WHERE nome LIKE '%juliana%' OR nome LIKE '%Juliana%'
        ORDER BY id
    """)
    results = cursor.fetchall()
    
    if results:
        print(f"   ✅ {len(results)} pessoa(s) encontrada(s):")
        for r in results:
            print(f"      ID: {r['id']} | Nome: {r['nome']} | Tipo: {r['tipo_cadastro']} | CRMV: {r['crmv']} | Ativo: {r['ativo']}")
    else:
        print("   ❌ Nenhuma pessoa com 'Juliana' no nome")
except Exception as e:
    print(f"   ❌ ERRO: {e}")

# 4. Listar TODOS os funcionários e veterinários
print("\n\n👥 TODOS OS FUNCIONÁRIOS E VETERINÁRIOS NA TABELA 'clientes':")
try:
    cursor.execute("""
        SELECT id, nome, tipo_cadastro, crmv, ativo
        FROM clientes
        WHERE tipo_cadastro IN ('funcionario', 'veterinario')
        ORDER BY id
    """)
    pessoas = cursor.fetchall()
    
    if pessoas:
        print(f"   ✅ {len(pessoas)} pessoa(s) encontrada(s):")
        for p in pessoas:
            print(f"      ID: {p['id']} | Nome: {p['nome']} | Tipo: {p['tipo_cadastro']} | CRMV: {p['crmv']} | Ativo: {p['ativo']}")
    else:
        print("   ❌ Nenhum funcionário/veterinário cadastrado")
except Exception as e:
    print(f"   ❌ ERRO: {e}")

# 5. Verificar comissões configuradas para ID 14 (se existir)
print("\n\n💰 COMISSÕES CONFIGURADAS PARA ID 14:")
try:
    cursor.execute("""
        SELECT 
            id,
            funcionario_id,
            tipo,
            tipo_calculo,
            percentual,
            ativo
        FROM comissoes_configuracao
        WHERE funcionario_id = 14
    """)
    configs = cursor.fetchall()
    
    if configs:
        print(f"   ✅ {len(configs)} configuração(ões) encontrada(s):")
        for cfg in configs:
            print(f"      Config ID: {cfg['id']} | Tipo: {cfg['tipo']} | Cálculo: {cfg['tipo_calculo']} | {cfg['percentual']}% | Ativo: {cfg['ativo']}")
    else:
        print("   ❌ Nenhuma configuração de comissão")
except Exception as e:
    print(f"   ❌ ERRO: {e}")

# 6. Verificar comissões GERADAS para ID 14
print("\n\n📊 COMISSÕES GERADAS (comissoes_itens) PARA ID 14:")
try:
    cursor.execute("""
        SELECT 
            id,
            venda_id,
            funcionario_id,
            valor_comissao,
            status,
            data_geracao
        FROM comissoes_itens
        WHERE funcionario_id = 14
        ORDER BY id
    """)
    itens = cursor.fetchall()
    
    if itens:
        print(f"   ✅ {len(itens)} comissão(ões) gerada(s):")
        total = 0
        for item in itens:
            print(f"      Comissão ID: {item['id']} | Venda: {item['venda_id']} | R$ {item['valor_comissao']:.2f} | Status: {item['status']}")
            total += item['valor_comissao']
        print(f"   💰 Total: R$ {total:.2f}")
    else:
        print("   ❌ Nenhuma comissão gerada")
except Exception as e:
    print(f"   ❌ ERRO: {e}")

# 7. Verificar ALL comissões órfãs (funcionario_id que não existe em clientes)
print("\n\n⚠️  COMISSÕES ÓRFÃS (funcionario_id não existe em clientes):")
try:
    cursor.execute("""
        SELECT DISTINCT ci.funcionario_id, COUNT(*) as qtde
        FROM comissoes_itens ci
        LEFT JOIN clientes c ON ci.funcionario_id = c.id
        WHERE c.id IS NULL
        GROUP BY ci.funcionario_id
    """)
    orfas = cursor.fetchall()
    
    if orfas:
        print(f"   ⚠️  {len(orfas)} funcionário(s) com comissões órfãs:")
        for o in orfas:
            print(f"      Funcionário ID: {o['funcionario_id']} | Quantidade: {o['qtde']} comissão(ões)")
    else:
        print("   ✅ Nenhuma comissão órfã encontrada")
except Exception as e:
    print(f"   ❌ ERRO: {e}")

conn.close()

print("\n" + "="*80)
print("✅ VERIFICAÇÃO CONCLUÍDA")
print("="*80)
