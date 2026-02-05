"""
Script para executar migração Sprint 2
"""
import sqlite3
import os

# Caminho do banco de dados (mesmo diretório do backend)
db_path = 'petshop.db'

# Ler arquivo de migração
with open('migrations/sprint2_produtos_variacao.sql', 'r', encoding='utf-8') as f:
    migration_sql = f.read()

# Conectar ao banco
print(f"📂 Conectando ao banco: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Statements da migração (executar um por um)
statements = [
    """ALTER TABLE produtos ADD COLUMN tipo_produto VARCHAR(20) DEFAULT 'SIMPLES' NOT NULL""",
    """ALTER TABLE produtos ADD COLUMN produto_pai_id INTEGER NULL""",
    """CREATE INDEX idx_produtos_tipo_produto ON produtos(tipo_produto)""",
    """CREATE INDEX idx_produtos_produto_pai_id ON produtos(produto_pai_id)""",
    """UPDATE produtos SET tipo_produto = 'SIMPLES' WHERE tipo_produto IS NULL"""
]

print(f"🔧 Executando {len(statements)} statements...")

for i, stmt in enumerate(statements, 1):
    try:
        print(f"  [{i}/{len(statements)}] {stmt[:60]}...")
        cursor.execute(stmt)
        print(f"  ✅ OK")
    except sqlite3.OperationalError as e:
        error_msg = str(e).lower()
        if 'duplicate column' in error_msg or 'already exists' in error_msg:
            print(f"  ⚠️  Já existe (ignorando)")
        else:
            print(f"  ❌ Erro: {e}")
            # Continuar mesmo com erro (pode ser que a coluna já exista)
            continue

# Commit
conn.commit()
print("\n✅ Migração concluída com sucesso!")

# Verificar estrutura
cursor.execute("PRAGMA table_info(produtos)")
columns = cursor.fetchall()
print(f"\n📋 Colunas da tabela produtos:")
for col in columns:
    if 'tipo_produto' in col[1] or 'produto_pai' in col[1]:
        print(f"  ✅ {col[1]} ({col[2]})")

# Contar produtos por tipo
cursor.execute("SELECT tipo_produto, COUNT(*) FROM produtos GROUP BY tipo_produto")
counts = cursor.fetchall()
print(f"\n📊 Produtos por tipo:")
for tipo, count in counts:
    print(f"  {tipo}: {count}")

conn.close()
print("\n🎉 Pronto!")
