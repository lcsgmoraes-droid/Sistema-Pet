"""
Investigar estrutura de AdquirentesTemplates
"""

import sys
sys.path.insert(0, r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("="*80)
print("ESTRUTURA DA TABELA adquirentes_templates".center(80))
print("="*80)

# Verificar estrutura
try:
    colunas = db.execute(text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'adquirentes_templates'
        ORDER BY ordinal_position
    """)).fetchall()
    
    print(f"\nColunas encontradas: {len(colunas)}")
    for col in colunas:
        print(f"   - {col[0]} ({col[1]})")
    
    # Buscar dados do template Stone (ID 1)
    print("\n" + "="*80)
    print("DADOS DO TEMPLATE STONE (ID 1)".center(80))
    print("="*80)
    
    template = db.execute(text("SELECT * FROM adquirentes_templates WHERE id = 1")).fetchone()
    if template:
        result = db.execute(text("SELECT * FROM adquirentes_templates LIMIT 0"))
        col_names = result.keys()
        
        print()
        for i, col_name in enumerate(col_names):
            print(f"   {col_name}: {template[i]}")
    
except Exception as e:
    print(f"   ⚠️ Erro: {str(e)}")

db.close()
