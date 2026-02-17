import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    # Buscar um produto para verificar encoding
    result = conn.execute(text("""
        SELECT id, nome, descricao, sku 
        FROM produtos 
        WHERE descricao IS NOT NULL AND descricao != ''
        LIMIT 3
    """))
    
    print("=== PRODUTOS NO BANCO ===")
    for row in result:
        print(f"ID: {row[0]}")
        print(f"Nome: {row[1]}")
        print(f"Descrição: {row[2]}")
        print(f"SKU: {row[3]}")
        print(f"Nome bytes: {row[1].encode('utf-8')}")
        print("-" * 50)
