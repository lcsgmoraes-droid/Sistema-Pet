#!/usr/bin/env bash
set -Eeuo pipefail

# COMPATIBILITY_ALIAS
# A correcao automatica antiga foi desativada. Este nome agora executa somente
# o diagnostico publico, sem alterar containers, arquivos ou banco.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
  echo "Python 3 nao encontrado para executar o diagnostico." >&2
  exit 1
}

echo "Atalho antigo detectado: executando diagnostico somente leitura."
exec "$PYTHON_BIN" "$SCRIPT_DIR/scripts/diagnosticar_producao_publica.py" "$@"
