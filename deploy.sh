#!/usr/bin/env bash
set -Eeuo pipefail

# Deploy principal do Pet Shop Pro.
# Mantido como atalho para o fluxo seguro atual, que:
# - exige repositorio limpo em producao;
# - gera o frontend em runtime/frontend/dist;
# - sobe postgres/backend/nginx, sem depender de servico frontend antigo;
# - valida watchdog e health publico antes de concluir.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/scripts/deploy_producao_seguro.sh" "$@"
