from sqlalchemy import create_engine, text
from app.config import get_database_url

engine = create_engine(get_database_url())

with engine.connect() as conn:
    result = conn.execute(text("SELECT id, name FROM roles"))
    roles = result.fetchall()
    print("📋 Roles existentes:")
    for row in roles:
        print(f"   {row[0]}: {row[1]}")
