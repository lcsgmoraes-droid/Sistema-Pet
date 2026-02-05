import sqlite3

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()

tabelas = ['vendas', 'vendas_itens', 'produtos', 'contas_pagar', 'formas_pagamento', 'vendas_pagamentos']

for tabela in tabelas:
    print(f"\n{'='*60}")
    print(f"TABELA: {tabela.upper()}")
    print('='*60)
    cursor.execute(f'PRAGMA table_info({tabela})')
    cols = cursor.fetchall()
    for c in cols:
        print(f"  {c[1]}")

conn.close()
