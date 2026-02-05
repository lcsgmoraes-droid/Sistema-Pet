import psycopg2

conn = psycopg2.connect('postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db')
cur = conn.cursor()

# Drop table antiga
cur.execute("DROP TABLE IF EXISTS configuracoes_entrega CASCADE")
conn.commit()
print('✅ Tabela configuracoes_entrega removida')

# Atualizar alembic_version para voltar para dee35922f6d0
cur.execute("UPDATE alembic_version SET version_num = 'dee35922f6d0'")
conn.commit()
print('✅ Alembic version resetada para dee35922f6d0')

conn.close()
