"""
Middlewares do Sistema Pet Shop Pro
====================================

Este módulo contém middlewares customizados para o FastAPI:

- TenantSecurityMiddleware: Validação global de tenant_id em requests autenticadas
"""

from .tenant_middleware import TenantSecurityMiddleware

__all__ = ["TenantSecurityMiddleware"]
