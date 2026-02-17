"""Ver colunas das tabelas vendas e venda_pagamentos"""

import sys
sys.path.insert(0, r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("Colunas da tabela 'vendas':")
cols = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'vendas' ORDER BY ordinal_position")).fetchall()
for c in cols:
    print(f"  - {c[0]}")

print("\nColunas da tabela 'venda_pagamentos':")
cols = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'venda_pagamentos' ORDER BY ordinal_position")).fetchall()
for c in cols:
    print(f"  - {c[0]}")

db.close()
