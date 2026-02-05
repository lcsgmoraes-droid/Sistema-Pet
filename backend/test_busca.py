import sqlite3

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()

# Simular a query do backend COM o JOIN
print('=== TESTANDO QUERY COM JOIN ===')
query = """
SELECT v.id, v.numero_venda, v.cliente_id, c.nome as cliente_nome
FROM vendas v
LEFT JOIN clientes c ON v.cliente_id = c.id
WHERE v.numero_venda LIKE ?
   OR c.nome LIKE ?
"""

busca = 'lucas'
cursor.execute(query, (f'%{busca}%', f'%{busca}%'))
resultados = cursor.fetchall()

print(f'Busca por "{busca}":')
print(f'Total de resultados: {len(resultados)}')
for r in resultados:
    print(f'  Venda #{r[0]} - {r[1]} - Cliente: {r[3] if r[3] else "Consumidor Final"}')

# Testar com case insensitive
print('\n=== TESTANDO COM ILIKE (case insensitive) ===')
cursor.execute("""
    SELECT v.id, v.numero_venda, v.cliente_id, c.nome as cliente_nome
    FROM vendas v
    LEFT JOIN clientes c ON v.cliente_id = c.id
    WHERE v.numero_venda LIKE ? COLLATE NOCASE
       OR c.nome LIKE ? COLLATE NOCASE
""", (f'%{busca}%', f'%{busca}%'))
resultados2 = cursor.fetchall()

print(f'Total de resultados: {len(resultados2)}')
for r in resultados2:
    print(f'  Venda #{r[0]} - {r[1]} - Cliente: {r[3] if r[3] else "Consumidor Final"}')

conn.close()
