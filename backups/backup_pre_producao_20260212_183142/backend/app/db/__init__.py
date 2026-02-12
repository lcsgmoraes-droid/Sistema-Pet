"""
Database utilities package.

This package contains database-related utilities and helpers for secure
multi-tenant operations and SQL auditing.

NOTE: For backwards compatibility, Base and other database objects 
are imported from the app.db module (not this package).
"""

# Import Base from db.py module for backwards compatibility
import sys
import os

# Tricky: Need to import from app.db (module) not app.db (package)
# Use direct import from db.py file
_parent_dir = os.path.dirname(os.path.dirname(__file__))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Import from db.py (same directory as parent)
import importlib.util
_db_module_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db.py')
_spec = importlib.util.spec_from_file_location("_db_module", _db_module_path)
_db_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_db_module)

# Export Base for backwards compatibility
Base = _db_module.Base
SessionLocal = _db_module.SessionLocal
engine = _db_module.engine
get_session = _db_module.get_session

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "get_session",
    "sql_audit",
]
