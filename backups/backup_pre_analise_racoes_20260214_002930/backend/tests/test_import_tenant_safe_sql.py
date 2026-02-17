"""
Teste simples de import do tenant_safe_sql
"""

def test_import_module():
    """Teste básico de import do módulo"""
    try:
        from app.utils.tenant_safe_sql import (
            execute_tenant_safe,
            execute_tenant_safe_scalar,
            execute_tenant_safe_one,
            execute_tenant_safe_first,
            execute_tenant_safe_all,
            TenantSafeSQLError
        )
        print("✅ Import successful!")
        assert execute_tenant_safe is not None
        assert TenantSafeSQLError is not None
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        raise


if __name__ == "__main__":
    test_import_module()
