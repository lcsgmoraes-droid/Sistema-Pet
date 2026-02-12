"""Script para testar a migration"""
from alembic.config import Config
from alembic import command
import traceback

try:
    cfg = Config('alembic.ini')
    command.upgrade(cfg, 'head')
    print("✓ SUCCESS: Migration aplicada com sucesso!")
except Exception as e:
    print(f"✗ ERROR: { str(e)}")
    traceback.print_exc()
