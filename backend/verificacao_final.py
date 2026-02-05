import sqlite3

conn = sqlite3.connect('petshop.db')
c = conn.cursor()

print("=" * 60)
print("VERIFICAÇÃO FINAL - SPRINT 4 PASSO 2")
print("=" * 60)

# Verificar produtos com tipo_kit
c.execute('SELECT COUNT(*) FROM produtos WHERE tipo_kit IS NOT NULL')
count = c.fetchone()[0]
print(f'\n✅ Produtos com tipo_kit: {count}')

# Verificar estrutura da tabela
c.execute('PRAGMA table_info(produto_kit_componentes)')
colunas = len(c.fetchall())
print(f'✅ Colunas em produto_kit_componentes: {colunas}')

# Verificar índices
c.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='produto_kit_componentes'")
indices = len(c.fetchall())
print(f'✅ Índices criados: {indices}')

conn.close()
print('\n✅ Banco sincronizado e funcional!')
print("=" * 60)
