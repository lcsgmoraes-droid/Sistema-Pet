import sqlite3
from uuid import UUID as PyUUID

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.compiler import compiles


sqlite3.register_adapter(PyUUID, lambda value: str(value))


@compiles(PGUUID, "sqlite")
def _compile_pg_uuid_for_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(type_, compiler, **kw):
    return "JSON"
