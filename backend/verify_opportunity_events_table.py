"""
Verificar estrutura da tabela opportunity_events
"""
import psycopg2

conn = psycopg2.connect('postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db')
cur = conn.cursor()

cur.execute("""
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name='opportunity_events' 
    ORDER BY ordinal_position
""")

cols = cur.fetchall()

print('\n✅ Estrutura da tabela opportunity_events:')
print('-' * 60)
for col in cols:
    nullable = 'NULL' if col[2] == 'YES' else 'NOT NULL'
    print(f'{col[0]:<25} {col[1]:<20} {nullable}')

# Verificar índices
cur.execute("""
    SELECT indexname FROM pg_indexes 
    WHERE tablename = 'opportunity_events'
""")
indexes = cur.fetchall()

print('\n✅ Índices criados:')
print('-' * 60)
for idx in indexes:
    print(f'  - {idx[0]}')

cur.close()
conn.close()
