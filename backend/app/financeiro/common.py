"""Dependencias compartilhadas do modulo financeiro."""

from fastapi import Depends

from app.security.module_access import require_active_module

financeiro_erp_required = Depends(require_active_module("financeiro_erp"))
