import os
from sqlalchemy import create_engine, inspect

# Pegar DATABASE_URL do .env
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

print("=== Verificação dos tipos de tenant_id ===\n")

tables = ['produtos', 'produto_config_fiscal', 'kit_config_fiscal']

for table in tables:
    columns = inspector.get_columns(table)
    tenant_col = [c for c in columns if c['name'] == 'tenant_id']
    if tenant_col:
        print(f"{table}.tenant_id: {tenant_col[0]['type']}")
    else:
        print(f"{table}: tenant_id não encontrado")

print("\n✅ Verificação concluída")
