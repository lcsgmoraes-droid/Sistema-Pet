#!/usr/bin/env bash
set -Eeuo pipefail

# COMPATIBILITY_ALIAS
# Atalho historico mantido para quem ainda usa `./deploy.sh` no servidor.
# A implementacao real e unica fica em scripts/deploy_producao_seguro.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Atalho de compatibilidade: iniciando o deploy seguro oficial."
exec "$SCRIPT_DIR/scripts/deploy_producao_seguro.sh" "$@"
