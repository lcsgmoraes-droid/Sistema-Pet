from sqlalchemy import inspect
from app.db import engine

insp = inspect(engine)

TABELAS = [
    "vendas",
    "venda_pagamentos",
    "venda_parcelas",
    "contas_receber",
    "contas_a_receber",
    "fluxo_caixa",
]

print("\n📦 LEVANTAMENTO DE ESTRUTURA — SOMENTE LEITURA\n")

tabelas_existentes = insp.get_table_names()

for tabela in TABELAS:
    if tabela in tabelas_existentes:
        print(f"\n=== TABELA: {tabela} ===")
        for col in insp.get_columns(tabela):
            print(f"- {col['name']} ({col['type']})")
    else:
        print(f"\n--- TABELA NÃO EXISTE: {tabela} ---")

print("\n✅ FIM DO LEVANTAMENTO (NENHUMA AÇÃO EXECUTADA)\n")
