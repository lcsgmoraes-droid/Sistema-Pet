# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('petshop.db')
cursor = conn.cursor()

print("\n=== ÚLTIMA VENDA ===\n")
cursor.execute("""
    SELECT id, numero_venda, vendedor_id, total, status, data_venda
    FROM vendas 
    ORDER BY id DESC 
    LIMIT 1
""")
venda = cursor.fetchone()
if venda:
    print(f"ID: {venda[0]}")
    print(f"Número: {venda[1]}")
    print(f"Vendedor ID: {venda[2]}")
    print(f"Total: R$ {venda[3]}")
    print(f"Status: {venda[4]}")
    print(f"Data: {venda[5]}")
else:
    print("Nenhuma venda encontrada")

print("\n=== CONFIGURAÇÕES DE COMISSÃO ATIVAS ===\n")
cursor.execute("""
    SELECT id, funcionario_id, tipo, referencia_id, tipo_calculo, percentual, ativo
    FROM comissoes_config
    WHERE ativo = 1
    ORDER BY id DESC
    LIMIT 5
""")
configs = cursor.fetchall()
if configs:
    for cfg in configs:
        print(f"ID: {cfg[0]} | Func: {cfg[1]} | Tipo: {cfg[2]} | Ref: {cfg[3]} | Calc: {cfg[4]} | %: {cfg[5]}")
else:
    print("❌ Nenhuma configuração ativa encontrada!")

conn.close()
