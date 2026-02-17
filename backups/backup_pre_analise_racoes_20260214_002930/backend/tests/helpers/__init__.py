"""
🧬 HELPERS DE TESTE - BLUEPRINT OFICIAL

Biblioteca reutilizável para testes consistentes em todos os módulos.

Uso:
    from tests.helpers import create_auth_header, assert_contract, assert_500
"""

from .auth import (
    create_auth_header,
    create_expired_token,
    create_invalid_token,
    create_token_without_tenant
)

from .tenant import (
    create_tenant_context,
    assert_tenant_isolation,
    get_default_tenant_id
)

from .contracts import (
    assert_contract,
    assert_date_format,
    assert_non_negative,
    assert_list_of_dicts,
    validate_schema
)

from .errors import (
    assert_500,
    assert_500_production,
    assert_500_development,
    assert_401,
    assert_429,
    assert_error_sanitized
)

__all__ = [
    # Auth
    "create_auth_header",
    "create_expired_token",
    "create_invalid_token",
    "create_token_without_tenant",
    
    # Tenant
    "create_tenant_context",
    "assert_tenant_isolation",
    "get_default_tenant_id",
    
    # Contracts
    "assert_contract",
    "assert_date_format",
    "assert_non_negative",
    "assert_list_of_dicts",
    "validate_schema",
    
    # Errors
    "assert_500",
    "assert_500_production",
    "assert_500_development",
    "assert_401",
    "assert_429",
    "assert_error_sanitized"
]
