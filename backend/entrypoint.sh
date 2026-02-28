#!/bin/bash
# =============================================================================
# ENTRYPOINT — Backend FastAPI
# Corrige permissões do diretório de uploads antes de iniciar a aplicação.
# Necessário porque o Docker Desktop (Windows) pode montar volumes com UID
# diferente do appuser (999), causando PermissionError nos uploads.
# =============================================================================
set -e

# Corrigir ownership do diretório de uploads se existir
if [ -d "/app/uploads" ]; then
    chown -R appuser:appuser /app/uploads 2>/dev/null || \
    chmod -R 777 /app/uploads 2>/dev/null || \
    true  # Se falhar (sem permissão), continua mesmo assim
fi

# Iniciar como appuser
exec gosu appuser "$@"
