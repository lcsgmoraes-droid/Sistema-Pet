import sqlite3

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()

# Executar a mesma query do endpoint
query = """
    SELECT DISTINCT 
        c.id,
        c.nome
    FROM clientes c
    WHERE c.id IN (
        SELECT DISTINCT funcionario_id 
        FROM comissoes_itens
        WHERE funcionario_id IS NOT NULL
    )
    ORDER BY c.nome ASC
"""

print("=" * 80)
print("EXECUTANDO QUERY DO ENDPOINT:")
print("=" * 80)
print(query)
print("\n" + "=" * 80)
print("RESULTADO:")
print("=" * 80)

cursor.execute(query)
rows = cursor.fetchall()

if rows:
    for row in rows:
        print(f"  ID: {row[0]}, Nome: {row[1]}")
    print(f"\nTotal: {len(rows)} funcionários encontrados")
else:
    print("  Nenhum funcionário encontrado!")
    
    # Debug: verificar se há dados
    print("\n" + "=" * 80)
    print("DEBUG - Funcionários em comissoes_itens:")
    print("=" * 80)
    cursor.execute("SELECT DISTINCT funcionario_id FROM comissoes_itens WHERE funcionario_id IS NOT NULL")
    func_ids = cursor.fetchall()
    print(f"  IDs: {[row[0] for row in func_ids]}")
    
    print("\n" + "=" * 80)
    print("DEBUG - Todos os clientes:")
    print("=" * 80)
    cursor.execute("SELECT id, nome FROM clientes LIMIT 10")
    clientes = cursor.fetchall()
    for row in clientes:
        print(f"  ID: {row[0]}, Nome: {row[1]}")

conn.close()
