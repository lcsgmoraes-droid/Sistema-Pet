"""Verificar estrutura real da tabela comissoes_configuracao"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

print("📋 Estrutura da tabela comissoes_configuracao:\n")
cursor.execute("PRAGMA table_info(comissoes_configuracao)")
colunas = cursor.fetchall()
for col in colunas:
    print(f"   {col['name']:30} {col['type']:15} NULL={'YES' if not col['notnull'] else 'NO':3}")

print("\n\n🔍 Dados na tabela:\n")
cursor.execute("SELECT * FROM comissoes_configuracao WHERE ativo = 1 LIMIT 5")
configs = cursor.fetchall()
if configs:
    for cfg in configs:
        print(f"   Config #{cfg['id']}:")
        for key in cfg.keys():
            print(f"      {key}: {cfg[key]}")
        print()
else:
    print("   (vazio)")

conn.close()
