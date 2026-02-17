"""
Buscar tabela com taxas de cartão
"""

import sys
sys.path.insert(0, r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Buscar operadora Stone com ID 1
operadora = db.execute(text("""
   SELECT * FROM operadoras_cartao WHERE id = 1
""")).fetchone()

if operadora:
    result = db.execute(text("SELECT * FROM operadoras_cartao LIMIT 0"))
    col_names = result.keys()
    
    print("="*80)
    print("OPERADORA ID 1 (Stone)".center(80))
    print("="*80)
    for i, col_name in enumerate(col_names):
        print(f"   {col_name}: {operadora[i]}")

# Agora vamos ver se existe alguma relação ou outra tabela com taxas
print("\n" + "="*80)
print("BUSCANDO TABELAS COM TAXAS".center(80))
print("="*80)

tables = db.execute(text("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND (table_name LIKE '%taxa%' OR table_name LIKE '%cartao%' OR table_name LIKE '%operadora%' OR table_name LIKE '%adquir%')
    ORDER BY table_name
""")).fetchall()

print(f"\nTabelas relacionadas: {[t[0] for t in tables]}")

# Verificar se existe tabela de formas de pagamento com taxas
print("\n" + "="*80)
print("ESTRUTURA formas_pagamento".center(80))
print("="*80)

try:
    colunas = db.execute(text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'formas_pagamento'
        ORDER BY ordinal_position
    """)).fetchall()
    
    print(f"\nColunas: {[c[0] for c in colunas]}")
    
    # Buscar dados
    formas = db.execute(text("SELECT * FROM formas_pagamento LIMIT 5")).fetchall()
    result_cols = db.execute(text("SELECT * FROM formas_pagamento LIMIT  0"))
    col_names = result_cols.keys()
    
    print(f"\nPrimeiras 5 formas:")
    for forma in formas:
        print(f"\n   ID {forma[0]}:")
        for i, col in enumerate(col_names):
            print(f"      {col}: {forma[i]}")
except Exception as e:
    print(f"   Erro: {str(e)}")
    db.rollback()

db.close()
