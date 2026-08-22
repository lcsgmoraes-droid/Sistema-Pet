#!/usr/bin/env bash
set -Eeuo pipefail

# COMPATIBILITY_ALIAS
# O script antigo alterava migrations e o banco diretamente. Esse comportamento
# foi aposentado. Qualquer correcao agora passa pelo mesmo fluxo seguro de deploy.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Fluxo antigo de correcao desativado: nenhum banco sera resetado."
echo "Iniciando o deploy seguro oficial."
exec "$SCRIPT_DIR/scripts/deploy_producao_seguro.sh" "$@"
