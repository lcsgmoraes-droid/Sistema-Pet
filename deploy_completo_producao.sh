#!/usr/bin/env bash
set -Eeuo pipefail

# COMPATIBILITY_ALIAS
# O fluxo antigo misturava Git, deploy, migrations e importacao de dados.
# O nome continua funcionando, mas agora usa somente o deploy seguro oficial.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Atalho antigo detectado: tarefas de importacao nao serao executadas."
echo "Iniciando somente o deploy seguro oficial."
exec "$SCRIPT_DIR/scripts/deploy_producao_seguro.sh" "$@"
