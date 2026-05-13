import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_database_url
from app.db.base_class import Base


DATABASE_URL = get_database_url()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


engine = create_engine(
    DATABASE_URL,
    pool_size=_env_int("SQLALCHEMY_POOL_SIZE", 10),
    max_overflow=_env_int("SQLALCHEMY_MAX_OVERFLOW", 20),
    pool_timeout=_env_int("SQLALCHEMY_POOL_TIMEOUT", 5),
    pool_recycle=_env_int("SQLALCHEMY_POOL_RECYCLE", 1800),
    pool_pre_ping=True,
    pool_use_lifo=True,
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
