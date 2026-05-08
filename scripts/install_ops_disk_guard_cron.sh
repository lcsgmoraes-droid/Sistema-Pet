#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/petshop}"
CRON_FILE="${DISK_GUARD_CRON_FILE:-/etc/cron.d/petshop-ops-disk-guard}"
SCHEDULE="${DISK_GUARD_CRON_SCHEDULE:-*/30 * * * *}"
WARNING_PERCENT="${DISK_GUARD_WARNING_PERCENT:-85}"
CRITICAL_PERCENT="${DISK_GUARD_CRITICAL_PERCENT:-90}"

if [[ "$(id -u)" != "0" ]]; then
  echo "Instalacao do cron exige root. Pulando disk guard cron." >&2
  exit 0
fi

if [[ ! -f "$APP_DIR/scripts/ops_disk_guard.sh" ]]; then
  echo "Script nao encontrado: $APP_DIR/scripts/ops_disk_guard.sh" >&2
  exit 0
fi

chmod +x "$APP_DIR/scripts/ops_disk_guard.sh"

cat >"$CRON_FILE" <<CRON
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

$SCHEDULE root APP_DIR=$APP_DIR DISK_GUARD_WARNING_PERCENT=$WARNING_PERCENT DISK_GUARD_CRITICAL_PERCENT=$CRITICAL_PERCENT $APP_DIR/scripts/ops_disk_guard.sh >/dev/null 2>&1
CRON

chmod 0644 "$CRON_FILE"
echo "Disk guard cron instalado em $CRON_FILE"
