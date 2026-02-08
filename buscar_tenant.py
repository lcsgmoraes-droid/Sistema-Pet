from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg2://postgres:postgres@localhost:5433/petshop_dev')
with engine.connect() as conn:
    result = conn.execute(text('SELECT id, name FROM tenants LIMIT 1'))
    tenant = result.fetchone()
    print(f'Tenant ID: {tenant[0]}')
    print(f'Nome: {tenant[1]}')
