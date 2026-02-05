from sqlalchemy import inspect
from app.db import engine

insp = inspect(engine)

def print_table(table_name):
    print(f"\n=== TABELA: {table_name} ===")
    cols = insp.get_columns(table_name)
    for c in cols:
        print(f"- {c['name']} ({c['type']})")

tables_of_interest = [
    'vendas',
    'venda_pagamentos',
    'venda_parcelas',
    'contas_receber',
    'contas_a_receber',
    'fluxo_caixa'
]

print("📦 TABELAS ENCONTRADAS NO BANCO:")
for t in insp.get_table_names():
    if t in tables_of_interest:
        print(f"✔ {t}")

for t in tables_of_interest:
    if t in insp.get_table_names():
        print_table(t)
