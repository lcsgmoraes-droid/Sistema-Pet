"""
⚠️  ESTE ARQUIVO FOI SUBSTITUÍDO PELA VERSÃO IDEMPOTENTE (Fase 5.3)
====================================================================

NOVO ARQUIVO: handlers_v53_idempotente.py

Este arquivo permanece apenas para compatibilidade de imports.
Todo o código foi migrado para a versão idempotente.

MUDANÇAS NA FASE 5.3:
- ✅ Todos handlers usam UPSERT (INSERT ... ON CONFLICT DO UPDATE)
- ✅ Nenhum handler faz commit() (responsabilidade do pipeline)
- ✅ Side effects protegidos com @suppress_in_replay
- ✅ Replay 2x = mesmo resultado
- ✅ Constraints de idempotência no banco
"""

# REDIRECIONAR para versão idempotente
from .handlers_v53_idempotente import (
    VendaReadModelHandler,
    registrar_handlers_read_models
)

__all__ = [
    'VendaReadModelHandler',
    'registrar_handlers_read_models'
]

import logging
logger = logging.getLogger(__name__)
logger.warning("⚠️  handlers.py DEPRECADO - redirecionando para handlers_v53_idempotente.py")
