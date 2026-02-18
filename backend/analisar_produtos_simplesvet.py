import csv
from pathlib import Path

# Ler produtos do SimplesVet
csv_path = Path(r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\simplesvet\banco\eco_produto.csv")
produtos = list(csv.DictReader(open(csv_path, encoding='utf-8')))

total = len(produtos)
com_sku = sum(1 for p in produtos if (p.get('pro_var_chave') or '').strip())
sem_sku = total - com_sku

print(f"═══════════════════════════════════════")
print(f"  ANÁLISE DOS PRODUTOS SIMPLESVET")
print(f"═══════════════════════════════════════")
print(f"Total produtos:  {total:,}")
print(f"Produtos COM SKU: {com_sku:,} ({com_sku/total*100:.1f}%)")
print(f"Produtos SEM SKU: {sem_sku:,} ({sem_sku/total*100:.1f}%)")
print(f"═══════════════════════════════════════")
