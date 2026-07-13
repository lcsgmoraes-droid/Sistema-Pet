#!/usr/bin/env bash
set -Eeuo pipefail

WRAPPER_PATH="${RESTORE_SMOKE_WRAPPER_PATH:-/usr/local/sbin/petshop-restore-smoke-producao}"
SUDOERS_FILE="${RESTORE_SMOKE_SUDOERS_FILE:-/etc/sudoers.d/petshop-restore-smoke}"
OPERATOR_USER="${RESTORE_SMOKE_OPERATOR_USER:-petdeploy}"

if [[ "$(id -u)" != "0" ]]; then
  echo "Instalacao do wrapper de restore smoke exige root." >&2
  exit 1
fi

command -v visudo >/dev/null 2>&1 || {
  echo "visudo nao encontrado; wrapper nao instalado." >&2
  exit 1
}
id "$OPERATOR_USER" >/dev/null 2>&1 || {
  echo "Usuario operacional nao encontrado: $OPERATOR_USER" >&2
  exit 1
}

wrapper_tmp="$(mktemp)"
sudoers_tmp="$(mktemp)"
cleanup() {
  rm -f "$wrapper_tmp" "$sudoers_tmp"
}
trap cleanup EXIT

cat >"$wrapper_tmp" <<'WRAPPER'
#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 0 ]]; then
  echo "Este wrapper nao aceita argumentos." >&2
  exit 2
fi

operator_user="${SUDO_USER:-unknown}"
cd /opt/petshop
exec env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root USER=root LOGNAME=root SUDO_USER="$operator_user" \
  APP_DIR=/opt/petshop \
  bash scripts/auditar_comando_producao.sh \
  --action database.restore_smoke \
  --reason validar-backup-e-restore-controlado \
  --label restore-smoke-em-container-descartavel \
  -- bash scripts/prod_db_restore_smoke.sh
WRAPPER

printf '%s ALL=(root) NOPASSWD: %s\n' "$OPERATOR_USER" "$WRAPPER_PATH" >"$sudoers_tmp"
chmod 0440 "$sudoers_tmp"
visudo -cf "$sudoers_tmp" >/dev/null

install -o root -g root -m 0755 "$wrapper_tmp" "$WRAPPER_PATH"
install -o root -g root -m 0440 "$sudoers_tmp" "$SUDOERS_FILE"
visudo -cf "$SUDOERS_FILE" >/dev/null

echo "Wrapper de restore smoke instalado em $WRAPPER_PATH"
