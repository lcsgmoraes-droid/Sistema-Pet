from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()
result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='dre_categorias' ORDER BY ordinal_position"))
print('Colunas dre_categorias:')
for row in result:
    print(f'  - {row[0]}')

result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='dre_subcategorias' ORDER BY ordinal_position"))
print('\nColunas dre_subcategorias:')
for row in result:
    print(f'  - {row[0]}')

db.close()
