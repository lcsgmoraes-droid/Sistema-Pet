"""
Teste rápido - Importar os próximos clientes (pulando os primeiros 20)
"""
from pathlib import Path
import csv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/petshop_dev"
SIMPLESVET_PATH = Path(r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\simplesvet\banco")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Ler CSV
with open(SIMPLESVET_PATH / 'glo_pessoa.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=',', quotechar='"')
    registros = list(reader)

# Pegar um cliente específico que deve ser novo (após o 20)
cliente = registros[25]  # Aleatório após os 20 primeiros

print("\nCliente de teste:")
print(f"- Código: {cliente.get('pes_var_chave')}")
print(f"- Nome: {cliente.get('pes_var_nome')}")
print(f"- Estado (original): '{cliente.get('end_var_uf')}'")
print(f"- Estado (len): {len(cliente.get('end_var_uf', ''))}")

# Processar estado
estado_raw = cliente.get('end_var_uf')
if estado_raw and estado_raw != 'NULL':
    estado = estado_raw.strip().upper()[:2]
else:
    estado = None

print(f"- Estado (processado): '{estado}'")
print(f"\nTodos os campos do CSV:")
for k, v in list(cliente.items())[:10]:
    print(f"  {k}: {v}")
