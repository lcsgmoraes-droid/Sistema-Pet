#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
CRON_FILE="${OPS_TLS_CRON_FILE:-/etc/cron.d/petshop-ops-tls-monitor}"
SCHEDULE="${OPS_TLS_CRON_SCHEDULE:-20 * * * *}"

if [[ "$(id -u)" != "0" ]]; then
  echo "Instalacao do cron exige root. Pulando monitor TLS." >&2
  exit 0
fi

if [[ ! -f "$APP_DIR/scripts/ops_tls_probe.sh" ]]; then
  echo "Script nao encontrado: $APP_DIR/scripts/ops_tls_probe.sh" >&2
  exit 1
fi

chmod +x "$APP_DIR/scripts/ops_tls_probe.sh"

cat >"$CRON_FILE" <<CRON
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

$SCHEDULE root flock -n /tmp/petshop-ops-tls-monitor.lock timeout 45 env APP_DIR=$APP_DIR $APP_DIR/scripts/ops_tls_probe.sh >>$APP_DIR/backend/logs/ops_tls_probe.log 2>&1
CRON

chmod 0644 "$CRON_FILE"
echo "Monitor TLS instalado em $CRON_FILE"
