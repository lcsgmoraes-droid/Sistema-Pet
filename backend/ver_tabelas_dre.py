from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()
result = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%dre%' ORDER BY table_name"))
print('Tabelas DRE:')
for r in result:
    print(f'  - {r[0]}')
db.close()
