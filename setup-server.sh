#!/usr/bin/env bash
set -Eeuo pipefail

# LEGACY_BLOCKED
# Este instalador de servidor foi criado para uma infraestrutura antiga e nao e
# compativel com a operacao atual. Ele fica como aviso para impedir uso acidental.

echo "Configuracao antiga de servidor bloqueada por seguranca." >&2
echo "Use docs/PRODUCAO_DEPLOY_SSH.md e o provisionamento autorizado atual." >&2
exit 1
