#!/usr/bin/env bash
set -Eeuo pipefail

# COMPATIBILITY_ALIAS
# Atalho historico do servidor. A logica operacional permanece centralizada no
# script seguro oficial.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Atalho antigo detectado: encaminhando para o deploy seguro oficial."
exec "$SCRIPT_DIR/scripts/deploy_producao_seguro.sh" "$@"
