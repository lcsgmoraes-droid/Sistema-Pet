"""
Teste minimalista para validar import
"""
import sys
import os
import pytest

# Garantir que o diretório backend está no path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


def test_import_works():
    """Teste básico de import"""
    from app.utils.tenant_safe_sql import execute_tenant_safe, TenantSafeSQLError
    assert execute_tenant_safe is not None
    assert TenantSafeSQLError is not None
    print("✅ Imports funcionando!")
