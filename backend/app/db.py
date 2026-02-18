from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_database_url
from app.db.base_class import Base

# Base para os modelos ORM (importada de base_class.py para compatibilidade com Alembic)

DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
