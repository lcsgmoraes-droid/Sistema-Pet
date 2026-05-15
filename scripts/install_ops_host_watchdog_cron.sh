#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
CRON_FILE="${HOST_WATCHDOG_CRON_FILE:-/etc/cron.d/petshop-ops-host-watchdog}"
SCHEDULE="${HOST_WATCHDOG_CRON_SCHEDULE:-* * * * *}"
PUBLIC_URL="${HOST_WATCHDOG_URL:-https://mlprohub.com.br/api/health/watchdog}"
FAILURE_THRESHOLD="${HOST_WATCHDOG_FAILURE_THRESHOLD:-3}"
RESTART_COOLDOWN_SECONDS="${HOST_WATCHDOG_RESTART_COOLDOWN_SECONDS:-300}"
MAX_RESTARTS_PER_WINDOW="${HOST_WATCHDOG_MAX_RESTARTS_PER_WINDOW:-3}"

if [[ "$(id -u)" != "0" ]]; then
  echo "Instalacao do cron exige root. Pulando host watchdog cron." >&2
  exit 0
fi

if [[ ! -f "$APP_DIR/scripts/ops_host_watchdog.sh" ]]; then
  echo "Script nao encontrado: $APP_DIR/scripts/ops_host_watchdog.sh" >&2
  exit 0
fi

chmod +x "$APP_DIR/scripts/ops_host_watchdog.sh"

cat >"$CRON_FILE" <<CRON
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

$SCHEDULE root APP_DIR=$APP_DIR HOST_WATCHDOG_URL=$PUBLIC_URL HOST_WATCHDOG_FAILURE_THRESHOLD=$FAILURE_THRESHOLD HOST_WATCHDOG_RESTART_COOLDOWN_SECONDS=$RESTART_COOLDOWN_SECONDS HOST_WATCHDOG_MAX_RESTARTS_PER_WINDOW=$MAX_RESTARTS_PER_WINDOW $APP_DIR/scripts/ops_host_watchdog.sh >/dev/null 2>&1
CRON

chmod 0644 "$CRON_FILE"
echo "Host watchdog cron instalado em $CRON_FILE"
