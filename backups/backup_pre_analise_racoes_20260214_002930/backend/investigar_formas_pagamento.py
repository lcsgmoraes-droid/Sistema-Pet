"""
Investigar formas de pagamento e suas taxas
"""

import sys
sys.path.insert(0, r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("="*80)
print("ESTRUTURA DA TABELA formas_pagamento".center(80))
print("="*80)

# Ver estrutura
colunas = db.execute(text("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'formas_pagamento'
    ORDER BY ordinal_position
""")).fetchall()

print(f"\nColunas ({len(colunas)}):")
for col in colunas:
    print(f"   - {col[0]} ({col[1]})")

# Buscar dados reais
print("\n" + "="*80)
print("FORMAS DE PAGAMENTO CADASTRADAS".center(80))
print("="*80)

formas = db.execute(text("""
    SELECT id, nome, tipo, operadora_id, taxa_percentual, taxas_por_parcela, ativo, max_parcelas
    FROM formas_pagamento
    WHERE ativo = true
    ORDER BY tipo, id
    LIMIT 20
""")).fetchall()

print(f"\n{len(formas)} formas ativas:")
for forma in formas:
    print(f"\n   ID {forma[0]}: {forma[1]}")
    print(f"      Tipo: {forma[2]}")
    print(f"      Operadora ID: {forma[3]}")
    print(f"      Taxa Percentual Padrão: {forma[4]}%")
    print(f"      Max Parcelas: {forma[7]}")
    print(f"      Taxas por Parcela: {forma[5]}")

# Buscar especificamente formas de cartão
print("\n" + "="*80)
print("CART\u00d5ES (Operadora Stone - ID 1)".center(80))
print("="*80)

cartoes = db.execute(text("""
    SELECT id, nome, tipo, taxa_percentual, taxas_por_parcela, max_parcelas
    FROM formas_pagamento
    WHERE operadora_id = 1
    AND tipo IN ('cartao_credito', 'cartao_debito')
    AND ativo = true
    ORDER BY tipo, id
""")).fetchall()

print(f"\n{len(cartoes)} formas encontradas:")
for cartao in cartoes:
    print(f"\n   {cartao[1]} (ID {cartao[0]})")
    print(f"      Tipo: {cartao[2]}")
    print(f"      Taxa Padrão: {cartao[3]}%")
    print(f"      Max Parcelas: {cartao[5]}")
    print(f"      Taxas por Parcela: {cartao[4]}")

db.close()
