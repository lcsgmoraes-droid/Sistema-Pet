"""
Aplicar migration de índices de performance
"""
from alembic import command
from alembic.config import Config

print("🔄 Aplicando migration de índices...")

cfg = Config("alembic.ini")
command.upgrade(cfg, "head")

print("✅ Migration aplicada com sucesso!")
print("\nÍndices criados:")
print("  - idx_contas_receber_tenant_nsu")
print("  - idx_contas_receber_conciliado")
print("  - idx_contas_receber_adquirente")
