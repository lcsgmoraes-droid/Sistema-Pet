"""
Investigar venda e seus pagamentos
"""

import sys
sys.path.insert(0, r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("="*80)
print("VENDA 202602130001 - ANÁLISE COMPLETA".center(80))
print("="*80)

# Buscar venda
venda = db.execute(text("""
    SELECT id, numero_venda, total
    FROM vendas
    WHERE numero_venda = '202602130001'
""")).fetchone()

print(f"\nVenda ID {venda[0]}: {venda[1]}")
print(f"Total: R$ {venda[2]:.2f}")

# Buscar pagamentos da venda
print("\n" + "="*80)
print("PAGAMENTOS".center(80))
print("="*80)

pagamentos = db.execute(text("""
    SELECT 
        vp.id,
        vp.valor,
        vp.operadora_id,
        vp.numero_parcelas,
        vp.forma_pagamento,
        fp.id as forma_id,
        fp.nome as forma_nome,
        fp.taxas_por_parcela,
        fp.taxa_percentual
    FROM venda_pagamentos vp
    LEFT JOIN formas_pagamento fp ON LOWER(fp.nome) = LOWER(vp.forma_pagamento)
    WHERE vp.venda_id = :venda_id
"""), {"venda_id": venda[0]}).fetchall()

print(f"\n{len(pagamentos)} pagamentos encontrados:")
for pag in pagamentos:
    print(f"\n   Pagamento ID {pag[0]}")
    print(f"      Valor: R$ {pag[1]:.2f}")
    print(f"      Operadora ID: {pag[2]}")
    print(f"      Numero Parcelas: {pag[3]}")
    print(f"      Forma Pagamento (string): {pag[4]}")
    print(f"      Forma Pagamento ID (join): {pag[5]}")
    print(f"      Forma Nome (join): {pag[6]}")
    print(f"      Taxa Percentual Padrão: {pag[8]}%")
    print(f"      Taxas por Parcela JSON: {pag[7]}")
    
    # Calcular taxa correta
    if pag[7] and pag[3]:
        import json
        from decimal import Decimal
        taxas_json = json.loads(pag[7])
        taxa_parcela = taxas_json.get(str(pag[3]))
        if taxa_parcela:
            valor_taxa = float(pag[1]) * (float(taxa_parcela) / 100)
            print(f"      >>> Taxa para {pag[3]} parcelas: {taxa_parcela}%")
            print(f"      >>> Valor da taxa: R$ {valor_taxa:.2f}")
        else:
            print(f"      >>> Parcela {pag[3]} não encontrada no JSON, usando taxa padrão")
            if pag[8]:
                valor_taxa = float(pag[1]) * (float(pag[8]) / 100)
                print(f"      >>> Valor da taxa (padrão): R$ {valor_taxa:.2f}")
    elif pag[8]:
        valor_taxa = float(pag[1]) * (float(pag[8]) / 100)
        print(f"      >>> Usando taxa padrão: {pag[8]}%")
        print(f"      >>> Valor da taxa: R$ {valor_taxa:.2f}")

db.close()
