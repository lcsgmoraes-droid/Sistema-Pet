"""
Script para editar a migration da tabela tenants
"""
import os
from pathlib import Path

# localizar a última migration criada
versions_path = Path('alembic/versions')
files = sorted(versions_path.glob('*.py'), key=os.path.getmtime, reverse=True)

if not files:
    print('❌ Nenhuma migration encontrada.')
    exit(1)

migration_file = files[0]
print(f'📄 EDITANDO MIGRATION: {migration_file.name}')

content = migration_file.read_text(encoding='utf-8')

# Substituir upgrade
upgrade_code = """def upgrade() -> None:
    import sqlalchemy as sa

    op.create_table(
        'tenants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='free'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )"""

downgrade_code = """def downgrade() -> None:
    op.drop_table('tenants')"""

# Substituir
content = content.replace('def upgrade() -> None:\n    pass', upgrade_code)
content = content.replace('def downgrade() -> None:\n    pass', downgrade_code)

migration_file.write_text(content, encoding='utf-8')

print('✅ Migration da tabela tenants criada e ajustada')
print('------------------------------------------------------------------')
print('CONTEÚDO FINAL DA MIGRATION:')
print('------------------------------------------------------------------')
print('')
print(content)
print('')
print('------------------------------------------------------------------')
print('📌 PRÓXIMA AÇÃO:')
print('  - Revisar o conteúdo acima')
print('  - Validar estrutura da tabela')
print('  - NÃO rodar alembic upgrade ainda')
print('==================================================================')
