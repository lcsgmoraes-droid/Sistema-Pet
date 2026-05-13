"""Database package exports.

The canonical SQLAlchemy objects live in app.db.core. This package reexports
them so existing imports keep using one Base, one engine and one SessionLocal.
"""

from app.db.core import Base, DATABASE_URL, SessionLocal, engine, get_session

# Hooks oficiais de multitenancy SQLAlchemy.
# app.db e carregado por praticamente toda a API; registrar aqui evita o modulo
# legado app.tenancy.sqlalchemy e garante fail-fast em queries e inserts.
import app.tenancy.filters  # noqa: E402,F401
import app.database.orm_guards  # noqa: E402,F401

__all__ = [
    "Base",
    "DATABASE_URL",
    "SessionLocal",
    "engine",
    "get_session",
    "sql_audit",
]
