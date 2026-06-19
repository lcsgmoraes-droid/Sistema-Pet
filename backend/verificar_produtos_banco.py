# ruff: noqa: E402

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.produtos_models import Produto
from sqlalchemy import func

db = SessionLocal()

try:
    # Contar produtos no banco
    total_produtos = db.query(func.count(Produto.id)).scalar()

    # Contar produtos com SKU válido
    produtos_com_sku = (
        db.query(func.count(Produto.id))
        .filter(Produto.codigo.isnot(None), Produto.codigo != "")
        .scalar()
    )

    print("═══════════════════════════════════════")
    print("  PRODUTOS NO BANCO DE DADOS")
    print("═══════════════════════════════════════")
    print(f"Total produtos:  {total_produtos:,}")
    print(f"Com SKU válido:  {produtos_com_sku:,}")
    print("═══════════════════════════════════════")
    print()
    print("📊 COMPARAÇÃO:")
    print("SimplesVet: 6.358 produtos com SKU")
    print(f"Banco atual: {produtos_com_sku:,} produtos")
    print(f"Faltam importar: {6358 - produtos_com_sku:,} produtos")
    print("═══════════════════════════════════════")

finally:
    db.close()
