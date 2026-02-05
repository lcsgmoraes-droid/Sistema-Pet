import sqlite3

conn = sqlite3.connect('petshop.db')
c = conn.cursor()

print("=== CORRIGINDO VENDAS ===\n")

# Buscar vendas com status incorreto
c.execute("""
    SELECT v.id, v.numero_venda, v.status, v.total, 
           COALESCE(SUM(vp.valor), 0) as total_pago
    FROM vendas v
    LEFT JOIN venda_pagamentos vp ON v.id = vp.venda_id
    WHERE date(v.data_venda) = date('now', 'localtime')
    GROUP BY v.id
""")

vendas = c.fetchall()
corrigidas = 0

for venda_id, numero, status_atual, total, total_pago in vendas:
    # Calcular status correto
    if total_pago == 0:
        status_correto = 'aberta'
    elif total_pago >= total - 0.01:  # Tolerância de 1 centavo
        status_correto = 'finalizada'
    else:
        status_correto = 'baixa_parcial'
    
    if status_atual != status_correto:
        print(f"Venda {numero} (ID {venda_id}):")
        print(f"  Status: {status_atual} → {status_correto}")
        print(f"  Total: R$ {total}, Pago: R$ {total_pago}")
        
        c.execute('UPDATE vendas SET status = ? WHERE id = ?', (status_correto, venda_id))
        corrigidas += 1
        print("  ✅ Corrigido!")
        print()

conn.commit()
print(f"\n✅ {corrigidas} vendas corrigidas!")

# Mostrar vendas com caixa_id None
print("\n" + "="*60)
print("VENDAS SEM CAIXA:")
c.execute("""
    SELECT id, numero_venda, status, total, data_venda
    FROM vendas
    WHERE caixa_id IS NULL
    AND date(data_venda) = date('now', 'localtime')
""")
sem_caixa = c.fetchall()
print(f"\n⚠️  {len(sem_caixa)} vendas sem caixa_id:")
for venda_id, numero, status, total, data in sem_caixa:
    print(f"  - Venda {numero} (ID {venda_id}): R$ {total}, {status}")

conn.close()

print("\n✅ Correção concluída!")
print("\n🔄 Recarregue a página no navegador (F5)")
