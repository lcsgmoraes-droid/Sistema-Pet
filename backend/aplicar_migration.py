"""Script para aplicar migration de entregador"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from alembic.config import Config
from alembic import command

alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")
print("✅ Migration aplicada com sucesso!")
