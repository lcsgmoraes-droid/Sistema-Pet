from sqlalchemy import create_engine, inspect

engine = create_engine('postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db')
inspector = inspect(engine)

print('Colunas da tabela permissions:')
for col in inspector.get_columns('permissions'):
    print(f"  - {col['name']} ({col['type']})")
