#!/usr/bin/env bash
set -Eeuo pipefail

# COMPATIBILITY_ALIAS
# Nome antigo preservado para nao quebrar atalhos locais ou guias historicos.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Atalho antigo detectado: encaminhando para o deploy seguro oficial."
exec "$SCRIPT_DIR/scripts/deploy_producao_seguro.sh" "$@"
