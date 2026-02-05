import sqlite3

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()

# Tabelas relevantes
tabelas = [
    'clientes',
    'vendas',
    'comissoes_configuracao',
    'comissoes_itens',
    'contas_pagar',
    'contas_receber',
    'movimentacoes_financeiras'
]

for tabela in tabelas:
    print(f"\n{'='*80}")
    print(f"TABELA: {tabela}")
    print('='*80)
    cursor.execute(f'PRAGMA table_info({tabela})')
    colunas = cursor.fetchall()
    for col in colunas:
        print(f"  {col[1]:30} {col[2]:15} {'PK' if col[5] else ''} {'NOT NULL' if col[3] else ''}")

conn.close()
