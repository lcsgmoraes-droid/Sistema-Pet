import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine
import sqlalchemy as sa

inspector = sa.inspect(engine)

print("=== produto_config_fiscal ===")
columns = inspector.get_columns('produto_config_fiscal')
for c in columns:
    print(f"{c['name']}: type={c['type']}")

print("\n=== kit_config_fiscal ===")
columns = inspector.get_columns('kit_config_fiscal')
for c in columns:
    print(f"{c['name']}: type={c['type']}")
