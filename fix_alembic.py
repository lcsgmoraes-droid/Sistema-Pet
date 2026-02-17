import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    conn.execute(text("UPDATE alembic_version SET version_num = '20260216_tenant_fluxo'"))
    conn.commit()
    print('Version updated to 20260216_tenant_fluxo')
