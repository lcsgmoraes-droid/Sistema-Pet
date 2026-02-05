"""
Script para verificar FKs órfãs na tabela produto_lotes
"""
from app.db import engine
from sqlalchemy import text

conn = engine.connect()

query = text("""
    SELECT 
        kcu.column_name,
        ccu.table_name AS foreign_table,
        ccu.column_name AS foreign_column,
        tc.constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu
        ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public'
        AND tc.table_name = 'produto_lotes'
""")

result = conn.execute(query)

print("=== FOREIGN KEYS em produto_lotes ===\n")
for row in result.fetchall():
    print(f"{row.column_name} -> {row.foreign_table}.{row.foreign_column}")
    print(f"  Constraint: {row.constraint_name}\n")

conn.close()
